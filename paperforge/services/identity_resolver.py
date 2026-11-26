"""Identity-first paper workspace, provenance, and anti-false-positive resolver.

Replaces brittle filename-prefix (`<KEY> - <Title>`), folder-depth, and
`slugify_filename(title)` heuristics with explicit structured identity anchors
while strictly protecting user copies, Obsidian `./assets` folders, native
`.base` files, symlinks/junctions, and cloud-sync conflict artifacts.
"""

from __future__ import annotations

import logging
import os
import re
import stat
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.adapters.obsidian_frontmatter import (
    read_frontmatter_dict,
    split_frontmatter_block,
)
from paperforge.worker.paper_meta import META_FILENAME, read_paper_meta

logger = logging.getLogger(__name__)

_NON_MAIN_FILENAMES = frozenset({"fulltext.md", "deep-reading.md", "discussion.md"})


def _nfc(text: str) -> str:
    """Normalize macOS APFS/HFS+ NFD filenames to NFC so cross-OS comparisons match."""
    return unicodedata.normalize("NFC", text)
_ZOTERO_KEY_RE = re.compile(r"^[A-Z0-9]{8}$")
_SYNC_CONFLICT_RE = re.compile(
    r"(?:\.sync-conflict-|conflicted copy|冲突副本|\bconflict\b.*\(\d+\))",
    re.IGNORECASE,
)
_PF_SIGNATURE_KEYS = frozenset({"ocr_status", "deep_reading_status", "do_ocr"})


def _norm_abs_path(path: Path) -> Path:
    """Fast case/separator-normalized absolute Path without touching symlink targets."""
    return Path(os.path.normcase(os.path.abspath(str(path))))


def is_reparse_or_symlink(path: Path) -> bool:
    """Return True if *path* is a symlink or Windows NTFS junction/reparse point (1 lstat syscall)."""
    try:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            return True
        if getattr(st, "st_file_attributes", 0) & 0x0400:  # FILE_ATTRIBUTE_REPARSE_POINT
            return True
    except OSError:
        return False
    return False


def is_sync_conflict_artifact(path: Path) -> bool:
    """Detect OneDrive / iCloud / Nutstore / Syncthing conflict copies."""
    return bool(_SYNC_CONFLICT_RE.search(path.name))


def read_text_tolerant(path: Path) -> tuple[str | None, str]:
    """Read text for inspection only without mutating non-UTF8 user files.

    Returns ``(decoded_text_or_none, encoding_status)`` where encoding_status is
    ``"utf-8"``, ``"utf-8-sig"``, ``"legacy_encoding"``, or ``"unreadable"``.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None, "unreadable"
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            return raw.decode("utf-8-sig"), "utf-8-sig"
        except UnicodeDecodeError:
            pass
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    for enc in ("gb18030", "utf-16"):
        try:
            return raw.decode(enc), "legacy_encoding"
        except UnicodeDecodeError:
            continue
    return None, "unreadable"


@dataclass
class WorkspaceIdentity:
    """Resolved workspace directory and associated notes for one Zotero key."""

    zotero_key: str
    workspace_dir: Path
    domain: str
    main_note_path: Path | None = None
    legacy_named_notes: list[Path] = field(default_factory=list)
    auxiliary_notes: list[Path] = field(default_factory=list)
    paper_meta_path: Path | None = None
    paper_meta: dict[str, Any] = field(default_factory=dict)
    identity_sources: tuple[str, ...] = ()
    has_workspace_fulltext: bool = False
    mismatches: list[str] = field(default_factory=list)


@dataclass
class FlatNoteIdentity:
    """Standalone note file carrying a structured ``zotero_key`` outside a workspace."""

    zotero_key: str
    note_path: Path
    domain: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    encoding_status: str = "utf-8"
    classification: str = "flat_note"  # "verified_legacy_flat" | "ambiguous_clone" | "user_copy"


@dataclass
class VaultIdentityScan:
    """Complete identity-first scan of ``lit_root``."""

    lit_root: Path
    workspaces: dict[str, WorkspaceIdentity] = field(default_factory=dict)
    duplicate_workspaces: dict[str, list[Path]] = field(default_factory=dict)
    flat_notes: list[FlatNoteIdentity] = field(default_factory=list)
    ambiguous_clones: list[FlatNoteIdentity] = field(default_factory=list)
    sync_conflicts: list[Path] = field(default_factory=list)
    symlinks_skipped: list[Path] = field(default_factory=list)
    orphan_workspaces: list[Path] = field(default_factory=list)
    mismatches: list[dict[str, Any]] = field(default_factory=list)


def _domain_for_path(lit_root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(lit_root)
        return _nfc(rel.parts[0]) if len(rel.parts) >= 2 else ""
    except ValueError:
        return ""


def _read_note_identity(
    note_path: Path,
    cache: dict[Path, tuple[str, dict[str, Any], str]] | None = None,
) -> tuple[str, dict[str, Any], str]:
    if cache is not None and note_path in cache:
        return cache[note_path]

    text: str | None = None
    enc_status = "utf-8"
    try:
        with open(note_path, "rb") as fh:
            head = fh.read(8192)
    except OSError:
        head = b""

    if head:
        decoded_head: str | None = None
        if head.startswith(b"\xef\xbb\xbf"):
            try:
                decoded_head = head.decode("utf-8-sig")
                enc_status = "utf-8-sig"
            except UnicodeDecodeError:
                decoded_head = None
        else:
            try:
                decoded_head = head.decode("utf-8")
                enc_status = "utf-8"
            except UnicodeDecodeError:
                decoded_head = None

        if decoded_head is not None and decoded_head.lstrip("\ufeff").startswith("---"):
            first_nl = decoded_head.find("\n")
            if first_nl >= 0 and (
                "\n---" in decoded_head[first_nl:] or "\r\n---" in decoded_head[first_nl:]
            ):
                text = decoded_head

    if text is None:
        text, enc_status = read_text_tolerant(note_path)

    if text is None:
        res: tuple[str, dict[str, Any], str] = ("", {}, enc_status)
        if cache is not None:
            cache[note_path] = res
        return res

    fm = read_frontmatter_dict(text)
    key = str(fm.get("zotero_key") or "").strip()
    if not key:
        # Fallback regex when hand-edited YAML has minor syntax errors
        m = re.search(r'^zotero_key:\s*["\']?([A-Za-z0-9]{8})["\']?\s*$', text[:4000], re.MULTILINE)
        if m:
            key = m.group(1).strip()
    res = (key, fm, enc_status)
    if cache is not None:
        cache[note_path] = res
    return res


def _has_paperforge_note_signature(fm: dict[str, Any]) -> bool:
    """Return True if *fm* carries PaperForge-specific workflow fields beyond a bare citekey."""
    return bool(fm.get("zotero_key")) and any(k in fm for k in _PF_SIGNATURE_KEYS)


def _extract_meaningful_body_lines(note_path: Path) -> set[str]:
    """Extract normalized non-empty prose lines outside YAML frontmatter & empty placeholders."""
    text, _ = read_text_tolerant(note_path)
    if not text:
        return set()
    split = split_frontmatter_block(text)
    body = split[1] if split is not None else text
    meaningful: set[str] = set()
    for raw_line in body.splitlines():
        s = raw_line.strip()
        if not s or s in ("---", "-", "*"):
            continue
        if "（待补充）" in s or "(待补充)" in s:
            continue
        meaningful.add(s)
    return meaningful


def is_verified_legacy_flat_note(
    flat: FlatNoteIdentity,
    workspace: WorkspaceIdentity | None,
    lit_root: Path,
) -> bool:
    """Four-Gate anti-false-positive check before treating a flat note as a migrated duplicate.

    1. Must sit directly inside ``<lit_root>/<domain>/<file>.md`` (legacy v1.0-v1.4 location).
    2. Filename must match generator naming (``<KEY>.md`` or ``<KEY> - <Title>.md``).
    3. Frontmatter must carry PaperForge workflow signature fields (not just a copied key).
    4. Must contain ZERO unique prose lines absent from ``workspace.main_note_path``
       (protects user reading copies / drafts created via Obsidian 'Make a copy').
    """
    if flat.encoding_status != "utf-8" and flat.encoding_status != "utf-8-sig":
        return False
    try:
        rel = flat.note_path.relative_to(lit_root)
    except ValueError:
        return False
    if len(rel.parts) != 2:
        return False
    stem = _nfc(flat.note_path.stem)
    key = flat.zotero_key
    if not (stem == key or stem.startswith(f"{key} - ")):
        return False
    if not _has_paperforge_note_signature(flat.frontmatter):
        return False
    if workspace is None or workspace.main_note_path is None or not workspace.main_note_path.is_file():
        return True
    flat_lines = _extract_meaningful_body_lines(flat.note_path)
    ws_lines = _extract_meaningful_body_lines(workspace.main_note_path)
    unique_to_flat = flat_lines - ws_lines
    return len(unique_to_flat) == 0


def _is_workspace_candidate(
    directory: Path,
    lit_root: Path,
    *,
    note_cache: dict[Path, tuple[str, dict[str, Any], str]] | None = None,
) -> bool:
    """Return True if *directory* has explicit PaperForge workspace provenance.

    Note: ``(directory / 'assets').is_dir()`` is intentionally NOT sufficient on
    its own because Obsidian users commonly set attachment subfolders to ``./assets``.
    """
    if directory == lit_root or is_reparse_or_symlink(directory):
        return False
    if (directory / META_FILENAME).is_file():
        return True
    if (directory / "annotations.jsonl").is_file() or (directory / "ai" / "memory-card.json").is_file():
        return True
    if (directory / "ai").is_dir() and " - " in directory.name:
        return True
    try:
        rel = directory.relative_to(lit_root)
        if len(rel.parts) >= 2:
            for child in directory.iterdir():
                if not child.is_file() or is_sync_conflict_artifact(child):
                    continue
                if child.suffix.lower() == ".md" and child.name.lower() not in _NON_MAIN_FILENAMES:
                    note_key, fm, _ = _read_note_identity(child, cache=note_cache)
                    c_stem = _nfc(child.stem)
                    d_name = _nfc(directory.name)
                    if note_key and (
                        c_stem == note_key
                        or (d_name == c_stem and _has_paperforge_note_signature(fm))
                    ):
                        return True
    except OSError:
        pass
    return False


def scan_vault_identities(lit_root: Path | None) -> VaultIdentityScan:
    """Scan *lit_root* in a single bounded pass without junctions, sync conflicts, or O(N^2) loops."""
    if lit_root is None or not lit_root.exists():
        return VaultIdentityScan(lit_root=lit_root or Path("."))

    root = Path(lit_root)
    scan = VaultIdentityScan(lit_root=root)
    if is_reparse_or_symlink(root):
        scan.symlinks_skipped.append(root)
        return scan

    note_cache: dict[Path, tuple[str, dict[str, Any], str]] = {}
    candidate_dirs: list[Path] = []
    walked_md_dirs: list[tuple[Path, list[Path]]] = []
    # Single safe os.walk with followlinks=False + explicit junction guard
    for dirpath_str, dirnames, filenames in os.walk(str(root), followlinks=False):
        cur_dir = Path(dirpath_str)
        kept_dirs: list[str] = []
        for dname in sorted(dirnames):
            if dname in (".obsidian", ".trash", ".git", "node_modules"):
                continue
            sub_p = cur_dir / dname
            if is_reparse_or_symlink(sub_p):
                scan.symlinks_skipped.append(sub_p)
                continue
            if is_sync_conflict_artifact(sub_p):
                scan.sync_conflicts.append(sub_p)
                continue
            kept_dirs.append(dname)
            if dname not in ("ai", "assets") and _is_workspace_candidate(
                sub_p, root, note_cache=note_cache
            ):
                candidate_dirs.append(sub_p)
        dirnames[:] = kept_dirs
        md_files: list[Path] = []
        for fname in sorted(filenames):
            fp = cur_dir / fname
            if is_sync_conflict_artifact(fp):
                scan.sync_conflicts.append(fp)
                continue
            if fname.lower().endswith(".md") and fname.lower() not in _NON_MAIN_FILENAMES:
                md_files.append(fp)
        if md_files:
            walked_md_dirs.append((cur_dir, md_files))

    # O(N * depth) deepest-workspace selection (replaces O(N^2) nested pair scan)
    norm_candidates = {d: _norm_abs_path(d) for d in candidate_dirs}
    ancestor_set: set[Path] = set()
    for norm_d in norm_candidates.values():
        ancestor_set.update(norm_d.parents)
    workspace_dirs = [
        d for d in sorted(candidate_dirs) if norm_candidates[d] not in ancestor_set
    ]

    seen_ws_files: set[Path] = set()
    for ws_dir in workspace_dirs:
        meta = read_paper_meta(ws_dir)
        meta_path = (ws_dir / META_FILENAME) if (ws_dir / META_FILENAME).is_file() else None
        meta_key = str(meta.get("zotero_key") or "").strip()

        note_records: list[tuple[Path, str, dict[str, Any]]] = []
        for child in sorted(ws_dir.iterdir()):
            if not child.is_file() or child.suffix.lower() != ".md" or is_sync_conflict_artifact(child):
                continue
            seen_ws_files.add(_norm_abs_path(child))
            if child.name.lower() in _NON_MAIN_FILENAMES:
                continue
            nkey, fm, _ = _read_note_identity(child, cache=note_cache)
            note_records.append((child, nkey, fm))

        sources: list[str] = []
        key_counts: dict[str, int] = {}
        if meta_key:
            key_counts[meta_key] = key_counts.get(meta_key, 0) + 1
            sources.append("paper-meta.json")
        for _, nkey, _ in note_records:
            if nkey:
                key_counts[nkey] = key_counts.get(nkey, 0) + 1
                if "frontmatter" not in sources:
                    sources.append("frontmatter")

        if not key_counts:
            scan.orphan_workspaces.append(ws_dir)
            continue

        if len(key_counts) > 1:
            scan.mismatches.append(
                {
                    "type": "workspace_key_conflict",
                    "path": str(ws_dir),
                    "keys": sorted(key_counts.keys()),
                }
            )
            canonical_key = meta_key or max(key_counts, key=lambda k: key_counts[k])
        else:
            canonical_key = next(iter(key_counts))

        dir_prefix = ws_dir.name.split(" - ", 1)[0].strip() if " - " in ws_dir.name else ""
        if dir_prefix and _ZOTERO_KEY_RE.match(dir_prefix) and dir_prefix != canonical_key:
            scan.mismatches.append(
                {
                    "type": "folder_prefix_key_mismatch",
                    "path": str(ws_dir),
                    "folder_prefix": dir_prefix,
                    "anchored_key": canonical_key,
                }
            )

        main_note: Path | None = None
        legacy_notes: list[Path] = []
        aux_notes: list[Path] = []
        exact_canonical = ws_dir / f"{canonical_key}.md"
        for child, nkey, _ in note_records:
            c_stem = _nfc(child.stem)
            if (child == exact_canonical or (c_stem == canonical_key and child.suffix.lower() == ".md")) and (
                not nkey or nkey == canonical_key
            ):
                main_note = child
            elif nkey == canonical_key and (c_stem == canonical_key or c_stem.startswith(f"{canonical_key} - ")):
                legacy_notes.append(child)
            else:
                aux_notes.append(child)
        if main_note is None and len(legacy_notes) == 1:
            main_note = legacy_notes.pop(0)

        ws_identity = WorkspaceIdentity(
            zotero_key=canonical_key,
            workspace_dir=ws_dir,
            domain=_domain_for_path(root, ws_dir),
            main_note_path=main_note,
            legacy_named_notes=legacy_notes,
            auxiliary_notes=aux_notes,
            paper_meta_path=meta_path,
            paper_meta=meta,
            identity_sources=tuple(sources),
            has_workspace_fulltext=(ws_dir / "fulltext.md").is_file(),
        )

        if canonical_key in scan.workspaces:
            dups = scan.duplicate_workspaces.setdefault(
                canonical_key, [scan.workspaces[canonical_key].workspace_dir]
            )
            dups.append(ws_dir)
            scan.mismatches.append(
                {
                    "type": "duplicate_workspace",
                    "zotero_key": canonical_key,
                    "paths": [str(p) for p in dups],
                }
            )
        else:
            scan.workspaces[canonical_key] = ws_identity

    # Inspect standalone markdown files outside workspaces using the single-walk cache
    ws_resolved_set = {_norm_abs_path(w.workspace_dir) for w in scan.workspaces.values()} | {
        _norm_abs_path(p) for dups in scan.duplicate_workspaces.values() for p in dups
    }
    for cur_dir, md_files in walked_md_dirs:
        cur_norm = _norm_abs_path(cur_dir)
        if cur_norm in ws_resolved_set or any(
            anc in ws_resolved_set for anc in cur_norm.parents
        ):
            continue
        if any(part in ("ai", "assets", ".obsidian", ".trash", ".git", "node_modules") for part in cur_norm.parts):
            continue
        for md_path in md_files:
            if _norm_abs_path(md_path) in seen_ws_files:
                continue
            nkey, fm, enc_status = _read_note_identity(md_path, cache=note_cache)
            if not nkey:
                continue
            flat_obj = FlatNoteIdentity(
                zotero_key=nkey,
                note_path=md_path,
                domain=_domain_for_path(root, md_path),
                frontmatter=fm,
                encoding_status=enc_status,
            )
            ws_match = scan.workspaces.get(nkey)
            if is_verified_legacy_flat_note(flat_obj, ws_match, root):
                flat_obj.classification = "verified_legacy_flat"
                scan.flat_notes.append(flat_obj)
            elif ws_match is not None:
                flat_obj.classification = "ambiguous_clone"
                scan.ambiguous_clones.append(flat_obj)
            else:
                flat_obj.classification = "standalone_note"
                scan.flat_notes.append(flat_obj)

    return scan


def resolve_workspace_by_key(
    vault: Path,
    zotero_key: str,
    *,
    lit_root: Path | None = None,
    db_first: bool = True,
) -> Path | None:
    """Resolve one paper's workspace directory using SQLite registry first, then identity scan."""
    key = str(zotero_key or "").strip()
    if not key:
        return None
    vault_root = Path(vault).expanduser().resolve()

    if db_first:
        try:
            from paperforge.memory.db import get_memory_db_path, open_live_reader

            db_path = get_memory_db_path(vault_root)
            if db_path.is_file():
                with open_live_reader(vault_root, db_path) as conn:
                    has_tbl = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='workspace_registry'"
                    ).fetchone()
                    if has_tbl:
                        row = conn.execute(
                            "SELECT workspace_relpath FROM workspace_registry WHERE zotero_key = ?",
                            (key,),
                        ).fetchone()
                        if row and row[0]:
                            candidate = (vault_root / str(row[0])).resolve()
                            if candidate.is_dir():
                                meta = read_paper_meta(candidate)
                                if meta.get("zotero_key") == key or (candidate / f"{key}.md").is_file():
                                    return candidate
        except Exception:  # noqa: BLE001
            pass

    if lit_root is None:
        try:
            from paperforge.config import paperforge_paths

            lit_root = paperforge_paths(vault_root).get("literature")
        except Exception:  # noqa: BLE001
            lit_root = vault_root / "Resources" / "Literature"

    scan = scan_vault_identities(lit_root)
    ws = scan.workspaces.get(key)
    return ws.workspace_dir if ws is not None else None
