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
``backups/fulltext.pre-rebuild.<ts>.md`` source).  Validated
``meta.json.restore_provenance`` persistence is delegated to the OCR
subsystem writer.  Structure, indexes, memory units and vectors are never
touched.
"""

from __future__ import annotations

import argparse
import datetime
import shutil
from pathlib import Path
from typing import Any

BACKUP_PREFIX = "fulltext.pre-rebuild."


def _safe_segment(name: str) -> bool:
    """A canonical single path segment: no separators, no dot segments."""
    return bool(name) and name not in (".", "..") and "/" not in name and "\\" not in name


def _safe_artifact_path(paper_root: Path, candidate: Path) -> str | None:
    """THE single exit for every presentation path handed to the UI.

    A DTO path is returned only when its RESOLVED form stays inside the
    paper root — a symlinked ``backups``/``render``/``versions`` subtree (or
    a symlinked paper directory) can never leak an out-of-root artifact path
    to a UI that is allowed to read Python-returned paths verbatim.
    """
    return str(candidate) if _contained(paper_root, candidate) else None


def _contained(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


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


def _backup_label(stamp: str, seq: str) -> str:
    """Label preserves sequence identity (``.001`` suffixes)."""
    return f"backup-{stamp}" + (f".{seq}" if seq else "")


def list_backups(paper_root: Path) -> list[dict[str, Any]]:
    """Legacy ``backups/fulltext.pre-rebuild.<stamp>[.<seq>].md`` recognition.

    Filename + timestamp semantics come from the producer's SSOT
    (``parse_pre_rebuild_backup_name`` / ``backup_stamp_to_iso``).
    """
    from paperforge.worker.ocr_fulltext_state import (
        backup_stamp_to_iso,
        parse_pre_rebuild_backup_name,
    )

    backups_dir = paper_root / "backups"
    if not backups_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for entry in sorted(backups_dir.iterdir()):
        parsed = parse_pre_rebuild_backup_name(entry.name)
        if parsed is None:
            continue
        safe_path = _safe_artifact_path(paper_root, entry)
        if safe_path is None:
            continue
        stamp, seq = parsed
        try:
            size = entry.stat().st_size
        except OSError:
            size = 0
        out.append(
            {
                "label": _backup_label(stamp, seq),
                "created_at": backup_stamp_to_iso(stamp),
                "source": "pre-rebuild",
                "fulltext_size": size,
                "source_path": safe_path,
            }
        )
    return out


def _authority_source(paper_root: Path, label: str) -> tuple[Path, str] | None:
    """Resolve a label through the AUTHORITY SETS only.

    The raw label string is never used as a path segment: it must exactly
    match a manifest version label or a recognized legacy backup label, and
    the source path is then constructed from the authority record. This
    makes cross-paper / dot-segment labels structurally impossible.
    """
    if not _safe_segment(label):
        return None
    manifest = read_manifest(paper_root)
    if manifest:
        for entry in manifest["versions"]:
            if isinstance(entry, dict) and str(entry.get("label")) == label:
                source = paper_root / "versions" / label / "fulltext.md"
                if _safe_artifact_path(paper_root, source) is not None:
                    return source, "version"
                return None
    for backup in list_backups(paper_root):
        if backup["label"] == label:
            source = Path(str(backup["source_path"]))
            if _safe_artifact_path(paper_root, source) is not None:
                return source, "legacy_backup"
            return None
    return None


def _entry_paths(paper_root: Path, label: str) -> dict[str, Any] | None:
    """Canonical artifact paths for an AUTHORITY-matched label, or None."""
    resolved = _authority_source(paper_root, label)
    if resolved is None:
        return None
    source, kind = resolved
    target = paper_root / "render" / "fulltext.md"
    safe_target = _safe_artifact_path(paper_root, target)
    if safe_target is None:
        return None
    return {
        "label": label,
        "kind": kind,
        "source_path": str(source),
        "current_path": safe_target,
    }


def _paper_root(vault: Path, key: str) -> Path | None:
    """OCR root's DIRECT canonical child — separators/dot segments refused."""
    if not _safe_segment(key):
        return None
    root = _ocr_root(vault) / key
    if not _contained(_ocr_root(vault), root):
        return None
    if root.resolve().parent != _ocr_root(vault).resolve():
        return None
    return root


def _with_paths(paper_root: Path, versions: list[Any]) -> list[dict[str, Any]]:
    """Attach the canonical artifact path to every version entry.

    Entries whose label is not a safe single segment, or whose resolved
    source escapes the paper root, are DROPPED — a corrupt manifest can
    never make Python hand the UI an out-of-root artifact path.
    """
    out: list[dict[str, Any]] = []
    for entry in versions:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label", ""))
        if not _safe_segment(label):
            continue
        source = paper_root / "versions" / label / "fulltext.md"
        safe_source = _safe_artifact_path(paper_root, source)
        if safe_source is None:
            continue
        enriched = dict(entry)
        enriched["source_path"] = safe_source
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
        "current_path": _safe_artifact_path(
            paper_root, paper_root / "render" / "fulltext.md"
        )
        or "",
        "total_size": total_size,
    }


def _run_list(vault: Path, version: str) -> int:
    root = _ocr_root(vault)
    papers: list[dict[str, Any]] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            # canonical direct child only: a symlinked paper entry must not
            # make the authority interpret a manifest outside the OCR root
            canonical = _paper_root(vault, child.name)
            if canonical is None or not canonical.is_dir():
                continue
            info = _paper_info(canonical)
            if info:
                papers.append(info)
    papers.sort(key=lambda p: p["title"].lower())
    print(_ok(version, {"intent": "versions-list", "papers": papers}).to_json())
    return 0


def _run_show(vault: Path, key: str, version: str) -> int:
    root = _paper_root(vault, key)
    if root is None or not root.is_dir():
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
                    "current_path": _safe_artifact_path(
                        root, root / "render" / "fulltext.md"
                    )
                    or "",
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
                "current_path": _safe_artifact_path(
                    root, root / "render" / "fulltext.md"
                )
                or "",
            },
        ).to_json()
    )
    return 0


def _run_backups(vault: Path, key: str, version: str) -> int:
    root = _paper_root(vault, key)
    if root is None or not root.is_dir():
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
    if root is None or not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    if not label:
        manifest = read_manifest(root)
        if not manifest:
            print(_err(version, f"no version manifest for {key}").to_json())
            return 1
        label = str(manifest["current"]["label"])
    paths = _entry_paths(root, label)
    if paths is None:
        print(_err(version, f"unknown version label for {key}: {label}").to_json())
        return 1
    if not Path(paths["source_path"]).exists():
        print(_err(version, f"version artifact not found for {key}/{label}").to_json())
        return 1
    print(_ok(version, {"intent": "versions-paths", "key": key, **paths}).to_json())
    return 0


def _run_restore(vault: Path, key: str, label: str, version: str) -> int:
    """Display-only restore with OCR-owned provenance validation.

    The displayed fulltext is authoritative for this operation.  Provenance
    is explanatory metadata, so the write is delegated to the OCR subsystem,
    which validates the payload and refuses to replace unreadable metadata.
    """
    root = _paper_root(vault, key)
    if root is None or not root.is_dir():
        print(_err(version, f"unknown paper key: {key}").to_json())
        return 1
    if not label:
        print(_err(version, "restore requires --label").to_json())
        return 1
    paths = _entry_paths(root, label)
    if paths is None:
        print(_err(version, f"unknown version label for {key}: {label}").to_json())
        return 1
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
    try:
        from paperforge.worker.ocr import record_restore_provenance

        provenance_persisted = record_restore_provenance(vault, key, provenance)
    except Exception:
        # Best-effort metadata: the restored bytes are authoritative.
        provenance_persisted = False
    print(
        _ok(
            version,
            {
                "intent": "versions-restore",
                "key": key,
                "label": label,
                "target_path": str(target),
                "provenance": provenance,
                "provenance_persisted": provenance_persisted,
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
