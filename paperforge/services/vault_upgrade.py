"""Cross-version Vault Census, Ownership Guard, Two-Speed Cutover, & Time-Machine Rollback (ADR-018).

Implements:
1. Three-Tier Veteran Detection (`detect_vault_provenance`): zero false positives on
   brand-new or foreign Obsidian + Zotero vaults.
2. Five-Bucket Full-Vault Census (`PF_MACHINE_PURE`, `PF_USER_ENRICHED`,
   `PF_CONFIRMED_RESIDUAL`, `USER_SOVEREIGN`, `AMBIGUOUS_OR_CLONE`).
3. Anti-false-positive guards for copied notes, native Obsidian `.base` files,
   `System/Attachments`, junctions/symlinks, sync conflicts, locked DBs, disk space,
   and external note backlinks (`aliases` preservation).
4. Two-Speed Progressive Migration:
   - `fast_cutover` (< 3s O(1) structural cutover) + 1-Click `rollback_vault_upgrade`
   - `heal_vault_progressive` (non-blocking background / JIT healing with Skip & Isolate).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.core.fs_safe import is_windows_reserved_name, safe_is_dir, safe_is_file, safe_iterdir
from paperforge.core.io import write_json_atomic, write_text_atomic

logger = logging.getLogger(__name__)

_PLUGIN_DEV_LEFTOVERS = (
    ".lintstagedrc",
    ".nvmrc",
    ".prettierrc",
    "CONTEXT.md",
    "DESIGN.md",
    "esbuild.config.mjs",
    "package.json",
    "package-lock.json",
    "tsconfig.json",
    "vitest.config.ts",
    "wdio.conf.mts",
)
_LEGACY_ENGINE_TEMP_NAMES = (
    "cli.py",
    "worker",
    "_tmp_ocr_list.json",
    "_tmp_pending_titles.json",
    "_tmp_ps.json",
    ".ocr_rebuild_checkpoint.json",
)
_STALE_PATH_PREFIXES = ("99_System/", "System/PaperForge/")
_LEGACY_SKILL_PARENTS = (".agents/skills", ".opencode/skills")


def _stale_path_prefixes_for_vault(vault_root: Path, configured_sys_dir: str = "") -> tuple[str, ...]:
    """Collect known legacy engine prefixes (hardcoded defaults + configured custom system_dir + backup metadata)."""
    prefixes: list[str] = ["System/PaperForge/", "99_System/PaperForge/", "99_System/"]
    candidates: list[str] = []
    if configured_sys_dir:
        candidates.append(configured_sys_dir)
    backups_root = vault_root / ".paperforge" / "backups"
    if backups_root.is_dir():
        for snap in sorted(backups_root.glob("upgrade-*"), reverse=True):
            meta_p = snap / "cutover-meta.json"
            if meta_p.is_file():
                with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
                    cm = json.loads(meta_p.read_text(encoding="utf-8"))
                    prev = str(cm.get("previous_system_dir") or "").strip()
                    if prev:
                        candidates.append(prev)
                break
    for raw in candidates:
        s = raw.replace("\\", "/").strip().strip("/")
        if not s or s == ".paperforge":
            continue
        pf_pref = f"{s}/PaperForge/"
        if pf_pref not in prefixes:
            prefixes.append(pf_pref)
        if s != "System":
            sys_pref = f"{s}/"
            if sys_pref not in prefixes:
                prefixes.append(sys_pref)
    return tuple(prefixes)


def _stale_engine_dir_prefixes(stale_prefixes: tuple[str, ...]) -> tuple[str, ...]:
    """Exact `<system_dir>/PaperForge/` prefixes safe to map to `.paperforge/`."""
    out: list[str] = []
    for p in stale_prefixes:
        if p.endswith("PaperForge/") or p == "99_System/PaperForge/":
            if p not in out:
                out.append(p)
    for p in ("System/PaperForge/", "99_System/PaperForge/"):
        if p not in out:
            out.append(p)
    return tuple(out)


def _rewrite_stale_engine_str(val: str, engine_prefixes: tuple[str, ...]) -> tuple[str, bool]:
    if not val:
        return val, False
    updated = val.replace("\\", "/")
    changed = False
    for pref in sorted(engine_prefixes, key=len, reverse=True):
        if updated.startswith(pref) or f"/{pref}" in updated or f"[[{pref}" in updated:
            updated = updated.replace(pref, ".paperforge/")
            changed = True
            break
    return updated, changed


_DB_TIER0_TABLE_MAP: tuple[tuple[str, str], ...] = (
    ("db_vec_body_rows", "vec_body_meta"),
    ("db_vec_objects_rows", "vec_objects_meta"),
    ("db_vec_fulltext_rows", "vec_fulltext_meta"),
    ("db_reading_log_rows", "reading_log"),
    ("db_project_log_rows", "project_log"),
    ("db_annotations_rows", "paper_annotations"),
    ("db_memory_cards_rows", "paper_memory_cards"),
)


def _capture_db_tier0_counts(db_path: Path) -> dict[str, int]:
    """Capture Tier-0 vector metadata and user log/annotation row counts from ``paperforge.db``."""
    counts = {key: 0 for key, _ in _DB_TIER0_TABLE_MAP}
    if not safe_is_file(db_path):
        return counts
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        existing = {
            str(r[0])
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for key, tbl in _DB_TIER0_TABLE_MAP:
            if tbl not in existing:
                continue
            row = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
            counts[key] = int(row[0]) if row else 0
    except sqlite3.Error:
        return counts
    finally:
        if conn is not None:
            with contextlib.suppress(sqlite3.Error):
                conn.close()
    return counts


def _capture_pre_upgrade_counts(
    vault_root: Path,
    engine_root: Path,
    lit_root: Path | None,
    *,
    fast_mode: bool = False,
    scan: Any | None = None,
    skip_workspace_scan: bool = False,
) -> dict[str, int]:
    """Capture non-zero lossless data invariants before any upgrade mutation."""
    candidate_db = engine_root / "indexes" / "paperforge.db"
    if not safe_is_file(candidate_db):
        candidate_db = vault_root / ".paperforge" / "indexes" / "paperforge.db"
    db_counts = _capture_db_tier0_counts(candidate_db)

    if fast_mode:
        tier0_valid = 0
        seen_ocr_keys: set[str] = set()
        for ocr_parent in (engine_root / "ocr", vault_root / ".paperforge" / "ocr"):
            if not safe_is_dir(ocr_parent):
                continue
            for pdir in safe_iterdir(ocr_parent):
                if not safe_is_dir(pdir) or pdir.name in seen_ocr_keys:
                    continue
                rj = pdir / "json" / "result.json"
                if safe_is_file(rj):
                    with contextlib.suppress(OSError):
                        if rj.stat().st_size > 2:
                            tier0_valid += 1
                            seen_ocr_keys.add(pdir.name)
        ws_count = 0
        if not skip_workspace_scan and lit_root and safe_is_dir(lit_root):
            for dom in safe_iterdir(lit_root):
                if not safe_is_dir(dom) or dom.name.startswith("."):
                    continue
                for ws in safe_iterdir(dom):
                    if safe_is_dir(ws) and ws.name not in ("ai", "assets"):
                        ws_count += 1
        return {
            "tier0_ocr_valid": tier0_valid,
            "workspaces": ws_count,
            "annotations_files": 0,
            "memory_card_files": 0,
            **db_counts,
        }

    from paperforge.materialization.ocr import validate_result_json
    from paperforge.services.identity_resolver import scan_vault_identities

    tier0_valid = 0
    seen_ocr_keys = set()
    ocr_pdirs: list[Path] = []
    for ocr_parent in (engine_root / "ocr", vault_root / ".paperforge" / "ocr"):
        if not safe_is_dir(ocr_parent):
            continue
        for pdir in safe_iterdir(ocr_parent):
            if not safe_is_dir(pdir) or pdir.name in seen_ocr_keys:
                continue
            seen_ocr_keys.add(pdir.name)
            ocr_pdirs.append(pdir)
    if ocr_pdirs:
        from paperforge.core.fs_safe import chunked_io_map

        res_list = chunked_io_map(lambda d: validate_result_json(d, fast=True), ocr_pdirs, chunk_size=64, min_parallel=32)
        tier0_valid = sum(1 for ok, _r, _p in res_list if ok)

    if skip_workspace_scan:
        return {
            "tier0_ocr_valid": tier0_valid,
            "workspaces": 0,
            "annotations_files": 0,
            "memory_card_files": 0,
            **db_counts,
        }

    scan = scan if scan is not None else scan_vault_identities(lit_root)
    ann_files = sum(1 for ws in scan.workspaces.values() if safe_is_file(ws.workspace_dir / "annotations.jsonl"))
    card_files = sum(1 for ws in scan.workspaces.values() if safe_is_file(ws.workspace_dir / "ai" / "memory-card.json"))
    return {
        "tier0_ocr_valid": tier0_valid,
        "workspaces": len(scan.workspaces),
        "annotations_files": ann_files,
        "memory_card_files": card_files,
        **db_counts,
    }
_PF_CONFIG_PROVENANCE_KEYS = frozenset(
    {
        "vault_config",
        "paddleocr_job_url",
        "paddleocr_model",
        "ocr_profile",
        "agent_platform",
        "agent_key",
        "paperforge_path",
    }
)


def _utcnow_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir_or_file_bytes(path: Path) -> int:
    from paperforge.services.identity_resolver import is_reparse_or_symlink

    if not path.exists() or is_reparse_or_symlink(path):
        return 0
    if path.is_file():
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0
    total = 0
    for root_s, dirs, files in os.walk(str(path), followlinks=False):
        rp = Path(root_s)
        dirs[:] = [d for d in dirs if not is_reparse_or_symlink(rp / d)]
        for fn in files:
            fp = rp / fn
            if not is_reparse_or_symlink(fp):
                with contextlib.suppress(OSError):
                    total += int(fp.stat().st_size)
    return total


def find_legacy_engine_dirs(vault_root: Path, configured_sys_dir: str = "") -> list[Path]:
    """Locate legacy ``<system_dir>/PaperForge`` directories case-insensitively.

    Supports both Windows/macOS case-insensitive mounts and Linux ext4 vaults
    where users or older configs created lowercase ``system/paperforge`` or
    ``99_system/paperforge`` folders.
    """
    from paperforge.services.identity_resolver import is_reparse_or_symlink

    target_names = {"system", "99_system"}
    cfg_clean = configured_sys_dir.strip().strip("/\\")
    if cfg_clean and cfg_clean != ".paperforge" and "/" not in cfg_clean and "\\" not in cfg_clean:
        target_names.add(cfg_clean.lower())

    candidate_parents: list[Path] = []
    for entry in safe_iterdir(vault_root):
        if is_reparse_or_symlink(entry) or not safe_is_dir(entry):
            continue
        if entry.name.lower() in target_names:
            candidate_parents.append(entry)

    if cfg_clean and cfg_clean != ".paperforge" and ("/" in cfg_clean or "\\" in cfg_clean):
        nested_parent = vault_root / cfg_clean.replace("\\", "/")
        if safe_is_dir(nested_parent) and not is_reparse_or_symlink(nested_parent):
            candidate_parents.append(nested_parent)

    found: list[Path] = []
    seen_resolved: set[Path] = set()
    for parent in candidate_parents:
        for child in safe_iterdir(parent):
            if is_reparse_or_symlink(child) or not safe_is_dir(child):
                continue
            if child.name.lower() != "paperforge":
                continue
            resolved = child.resolve()
            if resolved not in seen_resolved:
                seen_resolved.add(resolved)
                found.append(child)
    return sorted(found, key=lambda p: p.as_posix())


_find_legacy_engine_dirs = find_legacy_engine_dirs


def detect_vault_provenance(vault: Path) -> dict[str, Any]:
    """Classify *vault* into ``standard_current`` | ``veteran_legacy`` | ``veteran_rescue`` | ``fresh_or_foreign``."""
    from paperforge.services.vault_engine import CURRENT_LAYOUT_VERSION, read_vault_manifest

    vault_root = Path(vault).expanduser().resolve()
    manifest = read_vault_manifest(vault_root)
    tier1_evidence: list[str] = []
    tier2_evidence: list[str] = []

    has_legacy_engine = False
    seen_legacy_resolved: set[Path] = set()
    for legacy_cand in (vault_root / "System" / "PaperForge", vault_root / "99_System" / "PaperForge"):
        if legacy_cand.is_dir():
            has_legacy_engine = True
            seen_legacy_resolved.add(legacy_cand.resolve())
            tier1_evidence.append(f"legacy_engine_dir:{legacy_cand.relative_to(vault_root).as_posix()}")

    sys_d = ""
    cfg_path = vault_root / "paperforge.json"
    if cfg_path.is_file():
        try:
            raw_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(raw_cfg, dict) and (_PF_CONFIG_PROVENANCE_KEYS & set(raw_cfg.keys())):
                tier1_evidence.append("paperforge.json")
                vc = raw_cfg.get("vault_config") if isinstance(raw_cfg.get("vault_config"), dict) else {}
                sys_d = str(vc.get("system_dir") or raw_cfg.get("system_dir") or "")
                if sys_d and sys_d != ".paperforge" and (vault_root / sys_d / "PaperForge").is_dir():
                    has_legacy_engine = True
                    seen_legacy_resolved.add((vault_root / sys_d / "PaperForge").resolve())
                    tier1_evidence.append(f"configured_legacy_engine:{sys_d}/PaperForge")
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            tier1_evidence.append("paperforge.json:corrupt")

    for case_cand in _find_legacy_engine_dirs(vault_root, configured_sys_dir=sys_d):
        resolved = case_cand.resolve()
        if resolved not in seen_legacy_resolved:
            seen_legacy_resolved.add(resolved)
            has_legacy_engine = True
            tier1_evidence.append(f"legacy_engine_dir:{case_cand.relative_to(vault_root).as_posix()}")

    dot_pf = vault_root / ".paperforge"
    if dot_pf.is_dir() and any((dot_pf / sub).exists() for sub in ("indexes", "ocr", "trash", ".migration-journal.json")):
        tier1_evidence.append(".paperforge")

    plugin_data_path = vault_root / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if plugin_data_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            pdata = json.loads(plugin_data_path.read_text(encoding="utf-8"))
            if isinstance(pdata, dict) and any(
                pdata.get(k) for k in ("_setup_complete", "last_seen_version", "_migrated_keys", "zotero_data_dir")
            ):
                tier1_evidence.append("plugin_data.json")

    if (
        manifest is not None
        and int(manifest.get("layout_version") or 0) >= CURRENT_LAYOUT_VERSION
        and not has_legacy_engine
    ):
        return {
            "state": "standard_current",
            "needs_upgrade": False,
            "tier1_evidence": tier1_evidence,
            "tier2_evidence": tier2_evidence,
        }

    if tier1_evidence:
        return {
            "state": "veteran_legacy",
            "needs_upgrade": True,
            "tier1_evidence": tier1_evidence,
            "tier2_evidence": tier2_evidence,
        }

    # Tier-2 orphan rescue probe (bounded shallow check — never touches foreign vaults)
    for base_dir in (vault_root / "Bases", vault_root / "05_Bases"):
        if base_dir.is_dir():
            for bf in list(base_dir.glob("*.base"))[:20]:
                with contextlib.suppress(OSError):
                    txt = bf.read_text(encoding="utf-8", errors="ignore")
                    if "# PAPERFORGE_VIEW:" in txt or "paperforge-table" in txt:
                        tier2_evidence.append(f"base_signature:{bf.name}")
                        break

    for lit_cand in (vault_root / "Resources" / "Literature", vault_root / "03_Resources" / "Literature", vault_root / "Literature"):
        if lit_cand.is_dir():
            checked = 0
            for root_s, _dirs, files in os.walk(str(lit_cand), followlinks=False):
                rp = Path(root_s)
                if "paper-meta.json" in files:
                    with contextlib.suppress(OSError, json.JSONDecodeError):
                        pm = json.loads((rp / "paper-meta.json").read_text(encoding="utf-8"))
                        if isinstance(pm, dict) and "paperforge_version" in pm and "ocr_status" in pm:
                            tier2_evidence.append("workspace_paper_meta")
                            break
                for fn in files:
                    if fn.endswith(".md") and checked < 25:
                        checked += 1
                        with contextlib.suppress(OSError):
                            head = (rp / fn).read_text(encoding="utf-8", errors="ignore")[:2500]
                            if all(k in head for k in ("zotero_key:", "ocr_status:", "deep_reading_status:", "do_ocr:")):
                                tier2_evidence.append("note_4key_signature")
                                break
                if tier2_evidence or checked >= 25:
                    break

    if tier2_evidence:
        return {
            "state": "veteran_rescue",
            "needs_upgrade": True,
            "tier1_evidence": [],
            "tier2_evidence": tier2_evidence,
        }

    return {
        "state": "fresh_or_foreign",
        "needs_upgrade": False,
        "tier1_evidence": [],
        "tier2_evidence": [],
    }


def _is_paperforge_owned_base_file(txt: str, base_file: Path, known_domains: set[str]) -> bool:
    """Strictly distinguish PaperForge-managed `.base` files from user-created Obsidian `.base` files."""
    from paperforge.worker.base_views import PAPERFORGE_VIEW_PREFIX, RETIRED_PF_VIEWS

    if PAPERFORGE_VIEW_PREFIX in txt or "# paperforge-base-schema:" in txt or "paperforge-table" in txt:
        return True
    has_zotero_anchor = "zotero_key" in txt
    has_retired = any(rv in txt for rv in RETIRED_PF_VIEWS)
    norm_stem = unicodedata.normalize("NFC", base_file.stem)
    norm_domains = {unicodedata.normalize("NFC", d) for d in known_domains}
    if has_zotero_anchor and (has_retired or norm_stem in norm_domains or base_file.name == "Literature Hub.base"):
        return True
    if has_retired and base_file.name == "Literature Hub.base":
        return True
    # Allow explicit test/legacy domain base when name matches known domain or contains retired workflow view names
    if has_retired and any(f"name: {rv}" in txt or f'name: "{rv}"' in txt for rv in RETIRED_PF_VIEWS):
        return True
    return False


def _check_sqlite_movable(db_path: Path) -> tuple[bool, str]:
    """Non-destructively verify *db_path* is not write-locked on Windows OR POSIX."""
    if not db_path.is_file():
        return True, ""
    if os.name == "nt":
        try:
            with open(db_path, "r+b"):
                pass
        except OSError as exc:
            return False, str(exc)
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=0.25, isolation_level=None)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("ROLLBACK")
        return True, ""
    except sqlite3.Error as exc:
        return False, f"SQLite write lock active: {exc}"
    finally:
        if conn is not None:
            with contextlib.suppress(sqlite3.Error):
                conn.close()


def _check_disk_headroom(vault_root: Path, required_bytes: int) -> tuple[bool, int]:
    """Verify sufficient free disk headroom for snapshots, backups, and moves."""
    try:
        free_b = int(shutil.disk_usage(str(vault_root)).free)
    except OSError:
        return True, 0
    needed = max(required_bytes * 2 + 64 * 1024 * 1024, 64 * 1024 * 1024)
    return free_b >= needed, free_b


def _inject_backlink_alias(note_path: Path, old_stem: str) -> None:
    """Preserve `<KEY> - <Title>` inside YAML `aliases` so existing Obsidian `[[wikilinks]]` never break."""
    from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict

    with contextlib.suppress(OSError, UnicodeDecodeError):
        text = note_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return
        end_idx = text.find("\n---", 3)
        if end_idx == -1:
            return
        fm_part = text[:end_idx]
        existing_fm = read_frontmatter_dict(text)
        existing_aliases = existing_fm.get("aliases")
        if isinstance(existing_aliases, list):
            if any(str(a).strip() == old_stem for a in existing_aliases):
                return
        elif isinstance(existing_aliases, str) and existing_aliases.strip() == old_stem:
            return

        escaped = old_stem.replace('"', '\\"')
        if re.search(r"^aliases:\s*\[", fm_part, re.MULTILINE):
            new_fm = re.sub(
                r"^(aliases:\s*\[)(.*?)(\]\s*)$",
                lambda m: (
                    f'{m.group(1)}{m.group(2)}, "{escaped}"{m.group(3)}'
                    if m.group(2).strip()
                    else f'{m.group(1)}"{escaped}"{m.group(3)}'
                ),
                fm_part,
                count=1,
                flags=re.MULTILINE,
            )
        elif re.search(r"^aliases:\s*$", fm_part, re.MULTILINE):
            lines = fm_part.splitlines()
            out_lines: list[str] = []
            inserted = False
            i = 0
            while i < len(lines):
                line = lines[i]
                out_lines.append(line)
                if not inserted and re.match(r"^aliases:\s*$", line):
                    j = i + 1
                    while j < len(lines) and re.match(r"^\s+-\s+", lines[j]):
                        out_lines.append(lines[j])
                        j += 1
                    out_lines.append(f'  - "{escaped}"')
                    inserted = True
                    i = j
                    continue
                i += 1
            new_fm = "\n".join(out_lines)
        elif re.search(r"^aliases:\s+\S+", fm_part, re.MULTILINE):
            new_fm = re.sub(
                r"^aliases:\s+(.+?)\s*$",
                lambda m: f'aliases:\n  - "{m.group(1).strip().strip(chr(34)).strip(chr(39))}"\n  - "{escaped}"',
                fm_part,
                count=1,
                flags=re.MULTILINE,
            )
        elif "aliases:" not in fm_part:
            new_fm = fm_part + f'\naliases: ["{escaped}"]'
        else:
            return
        if new_fm != fm_part:
            write_text_atomic(note_path, new_fm + text[end_idx:])


def _snapshot_preflight_backups(
    vault_root: Path,
    engine_root: Path,
    configured_sys_dir: str,
    configured_base_dir: str = "",
) -> Path:
    """Create immutable pre-flight copies of small high-value files before any mutation.

    Never copies plaintext secret files (``.env``) into the backup directory.
    """
    snap_dir = vault_root / ".paperforge" / "backups" / f"upgrade-{_utcnow_compact()}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for rel in (
        "paperforge.json",
        ".obsidian/plugins/paperforge/data.json",
        ".obsidian/plugins/paperforge/manifest.json",
    ):
        src = vault_root / rel
        if src.is_file():
            dst = snap_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))

    base_dir_cands: list[str] = ["Bases", "05_Bases"]
    cfg_base_norm = configured_base_dir.replace("\\", "/").strip().strip("/")
    if cfg_base_norm and cfg_base_norm not in (".", "..") and cfg_base_norm not in base_dir_cands:
        base_dir_cands.append(cfg_base_norm)

    snapshotted_base_dirs: list[str] = []
    seen_base_dirs: set[Path] = set()
    for rel_b in base_dir_cands:
        base_dir = (vault_root / rel_b).resolve()
        if not base_dir.is_relative_to(vault_root) or base_dir == vault_root:
            continue
        if base_dir in seen_base_dirs or not base_dir.is_dir():
            continue
        seen_base_dirs.add(base_dir)
        copied_any = False
        for bf in base_dir.glob("*.base"):
            dst = snap_dir / bf.relative_to(vault_root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(bf), str(dst))
            copied_any = True
        if copied_any:
            snapshotted_base_dirs.append(base_dir.relative_to(vault_root).as_posix())

    idx_file = engine_root / "indexes" / "formal-library.json"
    if idx_file.is_file():
        shutil.copy2(str(idx_file), str(snap_dir / "formal-library.json"))

    dotenv_keys = _inspect_env_keys(vault_root / ".env")
    write_json_atomic(
        snap_dir / "cutover-meta.json",
        {
            "created_at": _utcnow_iso(),
            "previous_system_dir": configured_sys_dir,
            "previous_base_dir": cfg_base_norm or "Bases",
            "snapshotted_base_dirs": snapshotted_base_dirs,
            "legacy_engine_root": str(engine_root),
            "dotenv_present": bool(dotenv_keys),
            "dotenv_keys": dotenv_keys,
        },
    )
    return snap_dir


def _inspect_env_keys(env_path: Path) -> list[str]:
    if not env_path.is_file():
        return []
    keys: list[str] = []
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k = s.split("=", 1)[0].strip()
        if k:
            keys.append(k)
    return keys


def _detect_legacy_engine_root(vault_root: Path, configured_sys_dir: str) -> Path | None:
    candidates = [
        vault_root / configured_sys_dir / "PaperForge"
        if configured_sys_dir and configured_sys_dir != ".paperforge"
        else None,
        vault_root / "System" / "PaperForge",
        vault_root / "99_System" / "PaperForge",
    ]
    for cand in candidates:
        if cand is not None and cand.is_dir():
            return cand
    return None


def _resolve_layout_from_raw(vault_root: Path, cfg_raw: dict[str, Any]) -> dict[str, Any]:
    """Resolve layout roots from raw/legacy paperforge.json or filesystem probes when load_config raises ConfigError."""
    vc = cfg_raw.get("vault_config") if isinstance(cfg_raw.get("vault_config"), dict) else {}
    sys_dir = str(vc.get("system_dir") or cfg_raw.get("system_dir") or "System")
    skill_dir = str(vc.get("skill_dir") or cfg_raw.get("skill_dir") or ".opencode/skills")
    zotero_dir_val = str(cfg_raw.get("zotero_data_dir") or "")

    res_dir = str(vc.get("resources_dir") or cfg_raw.get("resources_dir") or "").strip()
    lit_sub = str(vc.get("literature_dir") or cfg_raw.get("literature_dir") or "Literature").strip() or "Literature"
    ctrl_sub = str(vc.get("control_dir") or cfg_raw.get("control_dir") or "LiteratureControl").strip() or "LiteratureControl"
    base_sub = str(vc.get("base_dir") or cfg_raw.get("base_dir") or "").strip()

    if res_dir:
        lit_root = vault_root / res_dir / lit_sub
        control_root = vault_root / res_dir / ctrl_sub
    elif not (vault_root / "Resources" / "Literature").is_dir() and (vault_root / "03_Resources" / "Literature").is_dir():
        lit_root = vault_root / "03_Resources" / "Literature"
        control_root = vault_root / "03_Resources" / "LiteratureControl"
    else:
        lit_root = vault_root / "Resources" / "Literature"
        control_root = vault_root / "Resources" / "LiteratureControl"

    if base_sub:
        base_root = vault_root / base_sub
    elif not (vault_root / "Bases").is_dir() and (vault_root / "05_Bases").is_dir():
        base_root = vault_root / "05_Bases"
    else:
        base_root = vault_root / "Bases"

    return {
        "system_dir": sys_dir,
        "skill_dir": skill_dir,
        "base_dir": base_sub or base_root.relative_to(vault_root).as_posix(),
        "zotero_data_dir": zotero_dir_val,
        "literature": lit_root,
        "control": control_root,
        "bases": base_root,
    }


def inspect_vault_upgrade(vault: Path, *, fast_summary: bool = False) -> dict[str, Any]:
    """Read-only Full-Vault Census & A/B/C Upgrade Plan with Five-Bucket Ownership classification."""
    from paperforge import __version__ as PF_VERSION
    from paperforge.config import ConfigError, load_config, resolve_paths, validate_config
    from paperforge.core.versioning import is_version_compatible
    from paperforge.credentials import CredentialKey, status as cred_status
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.runtime_pointer import read_pointer
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.migration_contract import (
        PER_FILE_ACTION_CONTRACT,
        audit_file_action_conflicts,
    )
    from paperforge.services.vault_engine import read_vault_manifest
    from paperforge.worker.base_views import RETIRED_PF_VIEWS

    vault_root = Path(vault).expanduser().resolve()
    provenance = detect_vault_provenance(vault_root)
    contract_conflicts = audit_file_action_conflicts()
    contract_count = len(PER_FILE_ACTION_CONTRACT)
    auto_items: list[dict[str, Any]] = []
    reconfig_items: list[dict[str, Any]] = []
    tamper_items: list[dict[str, Any]] = []
    cleanup_candidates: list[dict[str, Any]] = []

    if provenance["state"] == "fresh_or_foreign":
        return {
            "schema_version": 2,
            "vault": str(vault_root),
            "target_version": PF_VERSION,
            "provenance": provenance,
            "manifest_present": False,
            "manifest_state": {"heal_pending": False, "post_upgrade_sync_pending": False},
            "file_contract_conflicts": contract_conflicts,
            "file_contract_count": contract_count,
            "census": {
                "pf_machine_pure": 0,
                "pf_user_enriched": 0,
                "pf_confirmed_residual": 0,
                "user_sovereign_untouched": 0,
                "ambiguous_or_clone_frozen": 0,
            },
            "summary": {
                "auto_count": 0,
                "reconfig_critical_count": 0,
                "reconfig_minor_count": 0,
                "tamper_count": 0,
                "cleanup_candidate_count": 0,
                "cleanup_candidate_bytes": 0,
                "ocr_atoms": {"total": 0, "current": 0, "rebuild_derived_local": 0, "backfill_from_result_json": 0, "re_ocr_needed": 0},
            },
            "category_a_auto": [],
            "category_b_reconfig": [],
            "category_c_tamper": [],
            "cleanup_candidates": [],
        }

    manifest = read_vault_manifest(vault_root)
    cfg_path = vault_root / "paperforge.json"
    validation = validate_config(vault_root)
    cfg_raw: dict[str, Any] = {}
    if cfg_path.is_file():
        try:
            parsed = json.loads(cfg_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                cfg_raw = parsed
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            tamper_items.append(
                {
                    "id": "config.corrupt_json",
                    "area": "config",
                    "title": "配置文件 paperforge.json 语法损坏",
                    "detail": str(exc),
                    "remediation": "已锁定修改以防误覆盖，请先从备份恢复或重建配置。",
                }
            )

    if validation.state == "migration_required":
        auto_items.append(
            {
                "id": "config.migrate_v2",
                "area": "config",
                "title": "升级配置文件至规范结构",
                "count": 1,
                "fast_cutover": True,
                "detail": "将旧版顶层路径键与别名字段收敛到 vault_config。",
            }
        )

    configured_sys_dir = ""
    configured_skill_dir = ""
    lit_root = vault_root / "Resources" / "Literature"
    control_root = vault_root / "Resources" / "LiteratureControl"
    base_root = vault_root / "Bases"
    zotero_dir_val = ""
    try:
        snap = load_config(vault_root)
        configured_sys_dir = str(snap.values["system_dir"].value or "System")
        configured_skill_dir = str(snap.values["skill_dir"].value or ".agents/skills")
        zotero_dir_val = str(snap.values["zotero_data_dir"].value or "")
        paths = resolve_paths(vault_root, snap)
        lit_root = paths["literature"]
        control_root = paths.get("control") or control_root
        base_root = paths["bases"]
    except ConfigError:
        raw_layout = _resolve_layout_from_raw(vault_root, cfg_raw)
        configured_sys_dir = raw_layout["system_dir"]
        configured_skill_dir = raw_layout["skill_dir"]
        zotero_dir_val = raw_layout["zotero_data_dir"]
        lit_root = raw_layout["literature"]
        control_root = raw_layout["control"]
        base_root = raw_layout["bases"]
    stale_prefixes = _stale_path_prefixes_for_vault(vault_root, configured_sys_dir)

    dot_pf = vault_root / ".paperforge"
    legacy_pf = _detect_legacy_engine_root(vault_root, configured_sys_dir)
    journal_path = dot_pf / ".migration-journal.json"
    if journal_path.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            jdata = json.loads(journal_path.read_text(encoding="utf-8"))
            if jdata.get("state") == "in_progress":
                tamper_items.append(
                    {
                        "id": "storage.interrupted_journal",
                        "area": "storage",
                        "title": "检测到上次未完成的迁移事务日志",
                        "detail": "支持断点续传或按日志完整回退至迁移前原状。",
                        "remediation": "点击回退或继续完成迁移。",
                    }
                )

    if legacy_pf is not None:
        auto_items.append(
            {
                "id": "storage.move_to_dot_paperforge",
                "area": "storage",
                "title": f"将底层引擎目录 {legacy_pf.relative_to(vault_root).as_posix()} 收拢至隐藏目录 .paperforge/",
                "count": 1,
                "fast_cutover": True,
                "detail": "仅移动引擎专属子目录，保留 System/Attachments 等用户自有文件夹与可见笔记不动。",
            }
        )

    engine_root = legacy_pf if (legacy_pf is not None and not (dot_pf / "indexes").exists()) else dot_pf
    if manifest is None:
        auto_items.append(
            {
                "id": "manifest.initialize",
                "area": "engine",
                "title": "写入标准库布局清单 (.paperforge/vault-manifest.json)",
                "count": 1,
                "fast_cutover": True,
                "detail": "记录布局版本与备份快照路径，支持一键还原与后续无感升级。",
            }
        )

    # Runtime & Plugin checks
    pointer = read_pointer()
    if pointer is None:
        reconfig_items.append(
            {
                "id": "runtime.pointer_missing",
                "area": "runtime",
                "impact": "experience_critical",
                "title": "尚未准备独立 Python 运行环境",
                "detail": "后台同步与全文解析需要受管运行环境。",
                "remediation": "点击更新运行环境即可由 uv 自动配置隔离环境。",
            }
        )
    else:
        ptr_ver = str(pointer.get("paperforge_version") or "")
        compat_ok, _ = is_version_compatible(core_version=ptr_ver, expected_version=PF_VERSION)
        if not compat_ok:
            reconfig_items.append(
                {
                    "id": "runtime.pointer_stale",
                    "area": "runtime",
                    "impact": "experience_critical",
                    "title": f"运行环境版本较低（当前 {ptr_ver}，目标 {PF_VERSION}）",
                    "detail": f"当前指向 {pointer.get('python_path')}。",
                    "remediation": "一键更新至独立隔离运行环境，不影响本机其他 Python 项目。",
                }
            )

    corrupt_venv = vault_root / ".venv-corrupt"
    if corrupt_venv.exists():
        cleanup_candidates.append(
            {
                "id": "cleanup.venv_corrupt",
                "path": str(corrupt_venv),
                "bytes": _dir_or_file_bytes(corrupt_venv),
                "reason": "历史损坏的虚拟环境残留 (.venv-corrupt)",
            }
        )

    plugin_dir = vault_root / ".obsidian" / "plugins" / "paperforge"
    if plugin_dir.is_dir():
        for name in _PLUGIN_DEV_LEFTOVERS:
            lf = plugin_dir / name
            if lf.exists():
                cleanup_candidates.append(
                    {
                        "id": f"cleanup.plugin_dev.{lf.name}",
                        "path": str(lf),
                        "bytes": _dir_or_file_bytes(lf),
                        "reason": "插件目录中混入的开发工程残留文件",
                    }
                )
        pmanifest = plugin_dir / "manifest.json"
        if pmanifest.is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                pm = json.loads(pmanifest.read_text(encoding="utf-8"))
                pver = str(pm.get("version") or "")
                p_ok, _ = is_version_compatible(core_version=pver, expected_version=PF_VERSION)
                if pver and not p_ok:
                    reconfig_items.append(
                        {
                            "id": "plugin.version_behind",
                            "area": "plugin",
                            "impact": "experience_critical",
                            "title": f"Obsidian 插件文件待更新（当前 {pver}）",
                            "detail": "新版界面功能需要匹配的插件构建产物。",
                            "remediation": "更新插件文件（保留 data.json）并重载 Obsidian。",
                        }
                    )

    # Credentials & Zotero
    env_keys = _inspect_env_keys(vault_root / ".env")
    missing_creds = [
        kind for kind in ("ocr", "embedding") if cred_status(CredentialKey(kind)).state != "available"
    ]
    if env_keys and missing_creds:
        reconfig_items.append(
            {
                "id": "auth.env_migration_needed",
                "area": "auth",
                "impact": "experience_critical",
                "title": f".env 中的接口密钥尚未导入系统安全凭据库（缺少 {', '.join(missing_creds)}）",
                "detail": f"检测到键名: {', '.join(env_keys)}。",
                "remediation": "导入系统凭据库并通过校验后，原文件仍保留备份。",
            }
        )
    elif env_keys:
        reconfig_items.append(
            {
                "id": "auth.dotenv_still_present",
                "area": "auth",
                "impact": "minor",
                "title": ".env 仍存有历史明文密钥（系统凭据库已就绪）",
                "detail": "不影响正常使用，后续可按需脱敏归档。",
                "remediation": "可在空闲时手动归档 .env。",
            }
        )

    if zotero_dir_val:
        zp = Path(zotero_dir_val).expanduser()
        resolved_z = zp if zp.is_absolute() else (vault_root / zp)
        if not resolved_z.exists():
            reconfig_items.append(
                {
                    "id": "library.zotero_path_missing",
                    "area": "library",
                    "impact": "experience_critical",
                    "title": f"原 Zotero 数据目录当前不可达: {zotero_dir_val}",
                    "detail": "已有本地文献仍可正常阅读，但同步新文献前需重新指定目录。",
                    "remediation": "重新选择 Zotero 数据目录（或暂时跳过先读现有文献）。",
                }
            )
    elif provenance["state"] != "veteran_rescue":
        reconfig_items.append(
            {
                "id": "library.zotero_unconfigured",
                "area": "library",
                "impact": "experience_critical",
                "title": "尚未指定 Zotero 数据目录",
                "detail": "指定后即可同步文献附件。",
                "remediation": "在设置中选择 Zotero 数据目录。",
            }
        )

    # Workspaces & Five-Bucket Census
    stale_meta_paths: list[Path] = []
    legacy_named_note_count = 0
    ws_fulltext_count = 0
    user_aux_notes_count = 0
    if fast_summary:
        from paperforge.services.identity_resolver import VaultIdentityScan

        scan = VaultIdentityScan(lit_root=lit_root)
        fast_ws_count = 0
        fast_domains: set[str] = set()
        if safe_is_dir(lit_root):
            for dom in safe_iterdir(lit_root):
                if not safe_is_dir(dom) or dom.name.startswith("."):
                    continue
                fast_domains.add(dom.name)
                for ws_e in safe_iterdir(dom):
                    if safe_is_dir(ws_e) and ws_e.name not in ("ai", "assets"):
                        fast_ws_count += 1
    else:
        scan = scan_vault_identities(lit_root)
        fast_ws_count = len(scan.workspaces)
        fast_domains = {ws.domain for ws in scan.workspaces.values() if ws.domain}
        for ws in scan.workspaces.values():
            canonical_ws_note = ws.workspace_dir / f"{ws.zotero_key}.md"
            if (
                not canonical_ws_note.exists()
                and ws.main_note_path is not None
                and ws.main_note_path.stem.startswith(f"{ws.zotero_key} - ")
            ):
                legacy_named_note_count += 1
            else:
                legacy_named_note_count += len(ws.legacy_named_notes)
            user_aux_notes_count += len(ws.auxiliary_notes)
            if ws.has_workspace_fulltext:
                ws_fulltext_count += 1
            meta_json = ws.paper_meta or {}
            for field_name in ("ocr_md_path", "ocr_json_path", "fulltext_path"):
                val = str(meta_json.get(field_name) or "")
                if any(prefix in val for prefix in stale_prefixes) and ws.paper_meta_path is not None:
                    stale_meta_paths.append(ws.paper_meta_path)
                    break

    verified_flat = [f for f in scan.flat_notes if f.classification == "verified_legacy_flat"]
    if verified_flat or legacy_named_note_count or stale_meta_paths or ws_fulltext_count:
        auto_items.append(
            {
                "id": "workspaces.normalize_identities",
                "area": "workspaces",
                "title": "后台渐进规范化文献工作区与历史路径引用",
                "count": len(verified_flat) + legacy_named_note_count + len(stale_meta_paths) + ws_fulltext_count,
                "fast_cutover": False,
                "detail": (
                    f"后台静默整理：旧扁平镜像 {len(verified_flat)} 篇、旧命名主笔记 {legacy_named_note_count} 篇（自动写入双链别名）、"
                    f"过期路径元数据 {len(stale_meta_paths)} 份、工作区全文副本校验 {ws_fulltext_count} 份。"
                ),
            }
        )

    for mm in scan.mismatches:
        tamper_items.append(
            {
                "id": f"workspace.{mm.get('type')}",
                "area": "workspaces",
                "title": f"发现需核对的工作区状态 ({mm.get('type')})",
                "detail": json.dumps(mm, ensure_ascii=False),
                "remediation": "原目录已安全冻结保留在原处，不影响其他文献使用。",
            }
        )
    if scan.sync_conflicts:
        tamper_items.append(
            {
                "id": "workspace.sync_conflicts",
                "area": "workspaces",
                "title": f"检测到 {len(scan.sync_conflicts)} 个网盘同步冲突副本",
                "detail": ", ".join(p.name for p in scan.sync_conflicts[:5]),
                "remediation": "冲突副本已原样保留，绝不自动覆盖或清理。",
            }
        )

    # Atom-level OCR Tier-0 Truth Salvage
    ocr_dir = engine_root / "ocr"
    ocr_counts = {"total": 0, "current": 0, "rebuild_derived_local": 0, "backfill_from_result_json": 0, "re_ocr_needed": 0}
    backfill_keys: list[str] = []
    reocr_keys: list[str] = []
    if safe_is_dir(ocr_dir):
        if fast_summary:
            for oe in safe_iterdir(ocr_dir):
                if safe_is_dir(oe):
                    ocr_counts["total"] += 1
        else:
            ocr_subdirs = [pdir for pdir in safe_iterdir(ocr_dir) if safe_is_dir(pdir)]
            from paperforge.core.fs_safe import chunked_io_map

            atoms = chunked_io_map(lambda d: assess_ocr_bundle_atoms(d, fast=True), ocr_subdirs, chunk_size=64, min_parallel=32)
            for atom in atoms:
                ocr_counts["total"] += 1
                act = atom["salvage_action"]
                ocr_counts[act] = ocr_counts.get(act, 0) + 1
                if act in ("backfill_from_result_json", "rebuild_derived_local"):
                    backfill_keys.append(atom["zotero_key"])
                elif act == "re_ocr_needed":
                    reocr_keys.append(atom["zotero_key"])

    if backfill_keys:
        auto_items.append(
            {
                "id": "ocr.local_salvage_backfill",
                "area": "ocr",
                "title": f"从已保存的 OCR 原件免费离线恢复 {len(backfill_keys)} 篇派生全文",
                "count": len(backfill_keys),
                "keys": backfill_keys,
                "fast_cutover": False,
                "detail": "原始 json/result.json 完好无损，可在后台离线重建，无需重复消耗 OCR 额度。",
            }
        )
    if reocr_keys:
        reconfig_items.append(
            {
                "id": "ocr.missing_truth_reocr",
                "area": "ocr",
                "impact": "minor",
                "title": f"有 {len(reocr_keys)} 篇文献尚未完成全文解析",
                "count": len(reocr_keys),
                "keys": reocr_keys,
                "detail": "不影响升级与阅读其他文献，后续可在文献库按需勾选解析。",
                "remediation": "在文献库勾选需要阅读的条目点击「解析全文」即可。",
            }
        )

    # Base views (strictly guarding user-created native Obsidian `.base` files!)
    known_domains = set(fast_domains)
    exports_dir = engine_root / "exports"
    if exports_dir.is_dir():
        known_domains.update(p.stem for p in exports_dir.glob("*.json"))

    legacy_bases: list[dict[str, Any]] = []
    user_sovereign_bases = 0
    if base_root.is_dir():
        for bf in sorted(base_root.glob("*.base")):
            txt = bf.read_text(encoding="utf-8", errors="ignore")
            if not _is_paperforge_owned_base_file(txt, bf, known_domains):
                user_sovereign_bases += 1
                continue
            has_legacy_type = bool(re.search(r"^\s*-\s*type:\s*table\s*$", txt, re.MULTILINE))
            has_retired = any(rv in txt for rv in RETIRED_PF_VIEWS)
            unquoted_bang = bool(re.search(r"^\s*(?:-\s+)?!(?!\!)[^\n\"']+?\s*$", txt, re.MULTILINE))
            if has_legacy_type or has_retired or unquoted_bang:
                legacy_bases.append(
                    {
                        "path": str(bf),
                        "has_legacy_type": has_legacy_type,
                        "has_retired_views": has_retired,
                        "unquoted_filter": unquoted_bang,
                    }
                )
    if legacy_bases:
        auto_items.append(
            {
                "id": "bases.upgrade_views",
                "area": "bases",
                "title": f"升级 {len(legacy_bases)} 个文献库视图文件（保留您自建的视图与列宽）",
                "count": len(legacy_bases),
                "fast_cutover": True,
                "detail": "仅更新 PaperForge 预设视图，用户自建的其他 .base 文件原封不动。",
            }
        )

    # Zero-Vault-Pollution Skill Hub alignment + legacy v1.1/v1.2 library-records detection
    from paperforge.services.identity_resolver import is_reparse_or_symlink

    skill_cand_rels: list[str] = [f"{p}/paperforge" for p in _LEGACY_SKILL_PARENTS]
    cfg_skill_norm = configured_skill_dir.replace("\\", "/").strip("/")
    if cfg_skill_norm:
        cand_rel = f"{cfg_skill_norm}/paperforge"
        if cand_rel not in skill_cand_rels:
            skill_cand_rels.append(cand_rel)

    vault_local_skills: list[Path] = []
    seen_skill_resolved: set[str] = set()
    for srel in skill_cand_rels:
        sp = vault_root / srel
        if sp.exists() and not is_reparse_or_symlink(sp):
            rkey = os.path.normcase(str(sp.resolve()))
            if rkey in seen_skill_resolved:
                continue
            seen_skill_resolved.add(rkey)
            vault_local_skills.append(sp)
            slug = srel.replace("/", ".")
            cleanup_candidates.append(
                {
                    "id": f"cleanup.vault_local_skill.{slug}",
                    "path": str(sp),
                    "bytes": _dir_or_file_bytes(sp),
                    "reason": "旧版库内 AI Skill（新版已统一由本机 Skill Hub ~/.paperforge/skills/paperforge 管理，可安全移出 Vault 保持库目录整洁）",
                }
            )
    if vault_local_skills:
        reconfig_items.append(
            {
                "id": "skills.migrate_to_machine_hub",
                "area": "skills",
                "impact": "minor",
                "title": f"检测到 {len(vault_local_skills)} 处库内旧版 AI Skill，建议统一迁移至本机 Skill Hub",
                "detail": "新版 PaperForge 支持零 Vault 污染的本机 Skill Hub（~/.paperforge/skills/paperforge）+ MCP 自动注册与更新。",
                "remediation": "升级时将自动同步本机 Skill Hub，您也可在「存储与迁移维护」中安全移出库内旧副本。",
            }
        )

    lib_records_dir = control_root / "library-records"
    if safe_is_dir(lib_records_dir) and safe_iterdir(lib_records_dir):
        reconfig_items.append(
            {
                "id": "legacy.library_records_present",
                "area": "workspaces",
                "impact": "minor",
                "title": "检测到早期 v1.1/v1.2 library-records 目录",
                "detail": f"路径 {lib_records_dir.relative_to(vault_root).as_posix()} 为早期版本遗留档案目录，已安全原样保留。",
                "remediation": "确认其中无独有手写记录后，后续可按需自行归档。",
            }
        )

    # Database & cleanup candidates
    db_path = engine_root / "indexes" / "paperforge.db"
    if safe_is_file(db_path):
        movable, lock_err = _check_sqlite_movable(db_path)
        if not movable and legacy_pf is not None:
            tamper_items.append(
                {
                    "id": "db.file_locked",
                    "area": "database",
                    "title": "索引数据库当前正被其他程序占用",
                    "detail": lock_err,
                    "remediation": "请关闭占用数据库的工具或旧后台进程后再点击升级。",
                }
            )
        try:
            db_size = db_path.stat().st_size
            con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                if db_size < 64 * 1024 * 1024:
                    qc = con.execute("PRAGMA quick_check(1)").fetchone()
                    if not qc or str(qc[0]).lower() != "ok":
                        tamper_items.append(
                            {
                                "id": "db.integrity_failed",
                                "area": "database",
                                "title": "索引数据库自检发现坏块，需从本地文献重建",
                                "detail": str(qc[0] if qc else "unknown"),
                                "remediation": "自动备份旧库后从单篇笔记与 OCR 原件无损重建。",
                            }
                        )
                else:
                    con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
                    con.execute("PRAGMA schema_version").fetchone()
                    if con.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='papers'"
                    ).fetchone():
                        con.execute("SELECT COUNT(*) FROM papers").fetchone()
                tbls = {str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                if "workspace_registry" not in tbls or "ocr_catalog" not in tbls:
                    auto_items.append(
                        {
                            "id": "db.init_engine_ssot_tables",
                            "area": "database",
                            "title": "初始化统一高速索引表",
                            "count": 1,
                            "fast_cutover": False,
                            "detail": "后台同步工作区与 OCR 盘点索引，消除全库文件扫描卡顿。",
                        }
                    )
                else:
                    reg_cnt = int(con.execute("SELECT COUNT(*) FROM workspace_registry").fetchone()[0])
                    if fast_ws_count and reg_cnt == 0:
                        auto_items.append(
                            {
                                "id": "db.populate_workspace_registry",
                                "area": "database",
                                "title": "填充文献身份高速路由表",
                                "count": fast_ws_count,
                                "fast_cutover": False,
                                "detail": "将工作区身份映射写入 SQLite 索引。",
                            }
                        )
            finally:
                con.close()
        except sqlite3.Error as exc:
            tamper_items.append(
                {
                    "id": "db.unreadable",
                    "area": "database",
                    "title": "无法读取旧版索引数据库",
                    "detail": str(exc),
                    "remediation": "备份原文件后从单篇真相源无损重建。",
                }
            )
    elif fast_ws_count or ocr_counts["total"] > 0:
        auto_items.append(
            {
                "id": "db.create_from_truth",
                "area": "database",
                "title": "建立统一文献运行态索引库",
                "count": 1,
                "fast_cutover": False,
                "detail": "后台基于现有文献工作区与 OCR 原件建立高速索引。",
            }
        )

    if legacy_pf is not None:
        for rel_name in _LEGACY_ENGINE_TEMP_NAMES:
            p = legacy_pf / rel_name
            if p.exists():
                cleanup_candidates.append(
                    {
                        "id": f"cleanup.legacy_engine.{rel_name}",
                        "path": str(p),
                        "bytes": _dir_or_file_bytes(p),
                        "reason": "旧版引擎目录中的调试/临时缓存文件",
                    }
                )
    legacy_chroma_detected = False
    for idx_root in (engine_root / "indexes", dot_pf / "indexes"):
        if not idx_root.is_dir():
            continue
        vec_test = idx_root / "vectors_test"
        if vec_test.exists():
            cleanup_candidates.append(
                {
                    "id": "cleanup.vectors_test",
                    "path": str(vec_test),
                    "bytes": _dir_or_file_bytes(vec_test),
                    "reason": "早期测试版向量缓存目录 (vectors_test)",
                }
            )
        legacy_vec = idx_root / "vectors"
        if safe_is_dir(legacy_vec) and safe_iterdir(legacy_vec):
            legacy_chroma_detected = True
            cleanup_candidates.append(
                {
                    "id": "cleanup.legacy_chroma_vectors",
                    "path": str(legacy_vec),
                    "bytes": _dir_or_file_bytes(legacy_vec),
                    "reason": "旧版 ChromaDB 向量缓存（新版已改用 sqlite-vec，建议移入回收站后重新构建向量索引）",
                }
            )
        for bak in sorted(idx_root.glob("paperforge.db.bak-*")):
            cleanup_candidates.append(
                {
                    "id": f"cleanup.db_bak.{bak.name}",
                    "path": str(bak),
                    "bytes": _dir_or_file_bytes(bak),
                    "reason": "历史数据库恢复快照备份",
                }
            )
    if legacy_chroma_detected:
        reconfig_items.append(
            {
                "id": "vectors.rebuild_sqlite_vec",
                "area": "database",
                "impact": "minor",
                "title": "旧版 ChromaDB 向量索引需在新版中重新构建",
                "detail": "新版已移除 ChromaDB 依赖并切换为内置 sqlite-vec，升级后执行向量构建即可全新生成。",
                "remediation": "升级完成后在检索设置中点击「构建向量索引」或运行 paperforge embed。",
            }
        )

    # Deduplicate cleanup candidates by resolved path
    dedup_cleanup: list[dict[str, Any]] = []
    seen_cpaths: set[str] = set()
    for c in cleanup_candidates:
        rp_str = os.path.normcase(str(Path(c["path"]).resolve()))
        if rp_str not in seen_cpaths:
            seen_cpaths.add(rp_str)
            dedup_cleanup.append(c)

    census = {
        "pf_machine_pure": ocr_counts["total"] + ws_fulltext_count + len(verified_flat),
        "pf_user_enriched": fast_ws_count + len(legacy_bases),
        "pf_confirmed_residual": len(dedup_cleanup),
        "user_sovereign_untouched": user_sovereign_bases + user_aux_notes_count,
        "ambiguous_or_clone_frozen": len(scan.ambiguous_clones) + len(scan.duplicate_workspaces) + len(scan.sync_conflicts),
        "pf_canonical": {
            "workspaces": fast_ws_count,
        },
    }

    backups_root = vault_root / ".paperforge" / "backups"
    rollback_available = safe_is_dir(backups_root) and any(backups_root.glob("upgrade-*"))
    manifest_state = {
        "heal_pending": bool(manifest.get("heal_pending")) if isinstance(manifest, dict) else False,
        "post_upgrade_sync_pending": bool(manifest.get("post_upgrade_sync_pending"))
        if isinstance(manifest, dict)
        else False,
    }

    return {
        "schema_version": 2,
        "vault": str(vault_root),
        "target_version": PF_VERSION,
        "provenance": provenance,
        "manifest_present": manifest is not None,
        "manifest_state": manifest_state,
        "rollback_available": rollback_available,
        "file_contract_conflicts": contract_conflicts,
        "file_contract_count": contract_count,
        "census": census,
        "summary": {
            "auto_count": len(auto_items),
            "fast_cutover_count": sum(1 for a in auto_items if a.get("fast_cutover")),
            "progressive_heal_count": sum(1 for a in auto_items if not a.get("fast_cutover")),
            "reconfig_critical_count": sum(1 for r in reconfig_items if r.get("impact") == "experience_critical"),
            "reconfig_minor_count": sum(1 for r in reconfig_items if r.get("impact") == "minor"),
            "tamper_count": len(tamper_items),
            "cleanup_candidate_count": len(dedup_cleanup),
            "cleanup_candidate_bytes": sum(int(c.get("bytes") or 0) for c in dedup_cleanup),
            "ocr_atoms": ocr_counts,
        },
        "category_a_auto": auto_items,
        "category_b_reconfig": reconfig_items,
        "category_c_tamper": tamper_items,
        "cleanup_candidates": dedup_cleanup,
    }


def _strip_stale_paper_meta_paths(
    meta_path: Path,
    *,
    stale_prefixes: tuple[str, ...] | None = None,
) -> bool:
    prefixes = stale_prefixes or _STALE_PATH_PREFIXES
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    changed = False
    for field_name in ("ocr_md_path", "ocr_json_path", "fulltext_path"):
        val = str(data.get(field_name) or "")
        if any(prefix in val for prefix in prefixes):
            data.pop(field_name, None)
            changed = True
    if changed:
        write_json_atomic(meta_path, data)
    return changed


def _rel_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _reconcile_db_and_index_after_cutover(
    vault_root: Path,
    scan: Any,
    stale_prefixes: tuple[str, ...],
) -> dict[str, Any]:
    """Repair corrupt/missing DB from plaintext truth, rewrite stale engine paths, sync renamed notes, and hydrate missing sidecars."""
    from paperforge.memory.builder import (
        import_paper_annotations,
        import_paper_memory_cards,
        import_project_log,
        import_reading_log,
    )
    from paperforge.memory.db import WriterLock, check_and_heal_fts, get_connection, get_memory_db_path
    from paperforge.memory.schema import ensure_schema
    from paperforge.services.vault_engine import rebuild_db_from_truth

    db_path = get_memory_db_path(vault_root)
    engine_prefixes = _stale_engine_dir_prefixes(stale_prefixes)
    rebuilt_db = False
    db_paths_updated = 0
    sidecars_hydrated = 0
    warnings: list[str] = []

    db_corrupt_or_missing = not db_path.is_file()
    if db_path.is_file():
        try:
            con_ro = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                qc = con_ro.execute("PRAGMA quick_check").fetchone()
                if not qc or str(qc[0]).lower() != "ok":
                    db_corrupt_or_missing = True
            finally:
                con_ro.close()
        except sqlite3.Error:
            db_corrupt_or_missing = True

    formal_idx_path = vault_root / ".paperforge" / "indexes" / "formal-library.json"
    if formal_idx_path.is_file():
        try:
            raw_idx = json.loads(formal_idx_path.read_text(encoding="utf-8"))
            items_list = raw_idx if isinstance(raw_idx, list) else (raw_idx.get("items") if isinstance(raw_idx, dict) else None)
            if isinstance(items_list, list):
                idx_changed = False
                for entry in items_list:
                    if not isinstance(entry, dict):
                        continue
                    for fld in ("ocr_md_path", "ocr_json_path", "fulltext_path", "ai_path"):
                        nv, ch = _rewrite_stale_engine_str(str(entry.get(fld) or ""), engine_prefixes)
                        if ch:
                            entry[fld] = nv
                            idx_changed = True
                    ek = str(entry.get("zotero_key") or "").strip()
                    ws = scan.workspaces.get(ek)
                    if ws is not None and ws.main_note_path is not None and ws.main_note_path.is_file():
                        new_note_rel = _rel_posix(ws.main_note_path, vault_root)
                        if entry.get("main_note_path") != new_note_rel:
                            entry["main_note_path"] = new_note_rel
                            idx_changed = True
                        cur_np = str(entry.get("note_path") or "")
                        if cur_np and not (vault_root / cur_np).exists():
                            entry["note_path"] = new_note_rel
                            idx_changed = True
                if idx_changed:
                    write_json_atomic(formal_idx_path, raw_idx)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"formal-library reconcile skipped: {exc}")

    has_truth = bool(scan.workspaces) or (vault_root / ".paperforge" / "ocr").is_dir()
    if db_corrupt_or_missing and has_truth:
        if db_path.is_file():
            # Corrupt DB: move to backups before rebuilding
            bak_dir = vault_root / ".paperforge" / "backups" / f"db-corrupt-{_utcnow_compact()}"
            bak_dir.mkdir(parents=True, exist_ok=True)
            with contextlib.suppress(OSError):
                shutil.move(str(db_path), str(bak_dir / db_path.name))
        if formal_idx_path.is_file():
            try:
                rebuild_db_from_truth(vault_root, backup_existing=False)
                rebuilt_db = True
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"rebuild_db_from_truth warning: {exc}")
        elif db_path.is_file() or db_corrupt_or_missing:
            # No formal-library.json yet (e.g., partial/rescue test vault): initialize schema cleanly
            try:
                with WriterLock(vault_root):
                    conn_init = get_connection(db_path)
                    try:
                        ensure_schema(conn_init)
                        check_and_heal_fts(conn_init)
                        conn_init.commit()
                    finally:
                        conn_init.close()
                rebuilt_db = True
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"db init warning: {exc}")

    if db_path.is_file():
        try:
            with WriterLock(vault_root):
                conn = get_connection(db_path)
                try:
                    ensure_schema(conn)
                    check_and_heal_fts(conn)
                    paper_rows = conn.execute(
                        "SELECT zotero_key, ocr_md_path, ocr_json_path, fulltext_path, ai_path, main_note_path, note_path FROM papers"
                    ).fetchall()
                    for row in paper_rows:
                        zk = str(row["zotero_key"])
                        updates: dict[str, str] = {}
                        for col in ("ocr_md_path", "ocr_json_path", "fulltext_path", "ai_path"):
                            nv, ch = _rewrite_stale_engine_str(str(row[col] or ""), engine_prefixes)
                            if ch:
                                updates[col] = nv
                        ws = scan.workspaces.get(zk)
                        if ws is not None and ws.main_note_path is not None and ws.main_note_path.is_file():
                            new_rel = _rel_posix(ws.main_note_path, vault_root)
                            if str(row["main_note_path"] or "") != new_rel:
                                updates["main_note_path"] = new_rel
                            cur_note = str(row["note_path"] or "")
                            if cur_note and not (vault_root / cur_note).exists():
                                updates["note_path"] = new_rel
                        if updates:
                            set_clause = ", ".join(f"{c} = ?" for c in updates)
                            conn.execute(
                                f"UPDATE papers SET {set_clause} WHERE zotero_key = ?",
                                (*updates.values(), zk),
                            )
                            db_paths_updated += len(updates)

                    asset_rows = conn.execute("SELECT paper_id, asset_type, path FROM paper_assets").fetchall()
                    for arow in asset_rows:
                        nv, ch = _rewrite_stale_engine_str(str(arow["path"] or ""), engine_prefixes)
                        if ch:
                            conn.execute(
                                "UPDATE paper_assets SET path = ? WHERE paper_id = ? AND asset_type = ?",
                                (nv, arow["paper_id"], arow["asset_type"]),
                            )
                            db_paths_updated += 1

                    # Hydrate annotations / memory cards / logs if DB tables lack existing sidecar records
                    valid_keys = {str(r["zotero_key"]) for r in paper_rows}
                    if valid_keys:
                        ann_existing = {
                            str(r[0])
                            for r in conn.execute("SELECT DISTINCT paper_id FROM paper_annotations").fetchall()
                        }
                        card_existing = {
                            str(r[0])
                            for r in conn.execute("SELECT DISTINCT zotero_key FROM paper_memory_cards").fetchall()
                        }
                        ann_items: list[dict[str, str]] = []
                        card_items: list[dict[str, str]] = []
                        for zk in valid_keys:
                            ws = scan.workspaces.get(zk)
                            if ws is None:
                                continue
                            ws_rel = _rel_posix(ws.workspace_dir, vault_root)
                            if zk not in ann_existing and (ws.workspace_dir / "annotations.jsonl").is_file():
                                ann_items.append({"zotero_key": zk, "paper_root": ws_rel})
                            if zk not in card_existing and (ws.workspace_dir / "ai" / "memory-card.json").is_file():
                                card_items.append({"zotero_key": zk, "paper_root": ws_rel})
                        if ann_items:
                            sidecars_hydrated += import_paper_annotations(conn, vault_root, ann_items, valid_keys)
                        if card_items:
                            sidecars_hydrated += import_paper_memory_cards(conn, vault_root, card_items, valid_keys)

                        if (vault_root / ".paperforge" / "logs" / "reading-log.jsonl").is_file():
                            rl_cnt = int(conn.execute("SELECT COUNT(*) FROM reading_log").fetchone()[0])
                            if rl_cnt == 0:
                                sidecars_hydrated += int(
                                    import_reading_log(conn, vault_root, valid_keys).get("imported", 0)
                                )
                    if (vault_root / ".paperforge" / "logs" / "project-log.jsonl").is_file():
                        pl_cnt = int(conn.execute("SELECT COUNT(*) FROM project_log").fetchone()[0])
                        if pl_cnt == 0:
                            sidecars_hydrated += int(import_project_log(conn, vault_root))
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"db reconcile skipped: {exc}")

    return {
        "rebuilt_db": rebuilt_db,
        "db_paths_updated": db_paths_updated,
        "sidecars_hydrated": sidecars_hydrated,
        "warnings": warnings,
    }


def verify_vault_upgrade(
    vault: Path,
    *,
    pre_counts: dict[str, int] | None = None,
    stale_prefixes: tuple[str, ...] = (),
    check_healed_paths: bool = False,
    fast_mode: bool = False,
    scan: Any | None = None,
) -> dict[str, Any]:
    """Post-upgrade & post-heal hard reconciliation checks (Zero Silent Data Loss gate)."""
    from paperforge.config import ConfigError, resolve_paths, validate_config
    from paperforge.materialization.ocr import validate_result_json
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.vault_engine import read_vault_manifest

    vault_root = Path(vault).expanduser().resolve()
    checks: dict[str, bool] = {}
    failures: list[str] = []

    cfg_valid = validate_config(vault_root).state == "valid"
    checks["config_valid"] = cfg_valid
    if not cfg_valid:
        failures.append("paperforge.json is not valid v2 config")

    manifest = read_vault_manifest(vault_root)
    manifest_ok = manifest is not None and int(manifest.get("layout_version") or 0) >= 2
    checks["manifest_v2"] = manifest_ok
    if not manifest_ok:
        failures.append(".paperforge/vault-manifest.json missing or layout_version < 2")

    try:
        paths = resolve_paths(vault_root)
    except ConfigError:
        raw_cfg: dict[str, Any] = {}
        cfg_p = vault_root / "paperforge.json"
        if cfg_p.is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
                parsed = json.loads(cfg_p.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    raw_cfg = parsed
        paths = _resolve_layout_from_raw(vault_root, raw_cfg)

    lit_root = paths.get("literature")
    ocr_root = vault_root / ".paperforge" / "ocr"
    base_root = paths.get("bases")

    if fast_mode:
        fast_post = _capture_pre_upgrade_counts(vault_root, vault_root / ".paperforge", lit_root, fast_mode=True)
        tier0_valid = fast_post["tier0_ocr_valid"]
        ws_count = fast_post["workspaces"]
        ann_files = 0
        card_files = 0
        from paperforge.services.identity_resolver import VaultIdentityScan

        scan = VaultIdentityScan(lit_root=lit_root or (vault_root / "Resources" / "Literature"))
        known_domains: set[str] = set()
        if lit_root and safe_is_dir(lit_root):
            known_domains = {
                d.name
                for d in safe_iterdir(lit_root)
                if safe_is_dir(d) and not d.name.startswith(".")
            }
    else:
        tier0_valid = 0
        if safe_is_dir(ocr_root):
            ocr_pdirs = [pdir for pdir in safe_iterdir(ocr_root) if safe_is_dir(pdir)]
            from paperforge.core.fs_safe import chunked_io_map

            res_list = chunked_io_map(lambda d: validate_result_json(d, fast=True), ocr_pdirs, chunk_size=64, min_parallel=32)
            tier0_valid = sum(1 for ok, _r, _p in res_list if ok)

        scan = scan if scan is not None else scan_vault_identities(lit_root)
        ws_count = len(scan.workspaces)
        ann_files = sum(1 for ws in scan.workspaces.values() if safe_is_file(ws.workspace_dir / "annotations.jsonl"))
        card_files = sum(1 for ws in scan.workspaces.values() if safe_is_file(ws.workspace_dir / "ai" / "memory-card.json"))
        known_domains = {ws.domain for ws in scan.workspaces.values() if ws.domain}

    db_path = vault_root / ".paperforge" / "indexes" / "paperforge.db"
    db_tier0_post = _capture_db_tier0_counts(db_path)
    post_counts = {
        "tier0_ocr_valid": tier0_valid,
        "workspaces": ws_count,
        "annotations_files": ann_files,
        "memory_card_files": card_files,
        **db_tier0_post,
    }

    if pre_counts is not None:
        ocr_ok = tier0_valid >= int(pre_counts.get("tier0_ocr_valid", 0))
        checks["tier0_ocr_preserved"] = ocr_ok
        if not ocr_ok:
            failures.append(f"tier0_ocr_valid dropped: {pre_counts.get('tier0_ocr_valid')} -> {tier0_valid}")
        ws_ok = ws_count >= int(pre_counts.get("workspaces", 0))
        checks["workspaces_preserved"] = ws_ok
        if not ws_ok:
            failures.append(f"workspaces dropped: {pre_counts.get('workspaces')} -> {ws_count}")
        if not fast_mode:
            sidecar_ok = (
                ann_files >= int(pre_counts.get("annotations_files", 0))
                and card_files >= int(pre_counts.get("memory_card_files", 0))
            )
            checks["sidecars_preserved"] = sidecar_ok
            if not sidecar_ok:
                failures.append("workspace annotation or memory-card files missing after upgrade")

        db_sovereignty_ok = True
        for db_key in db_tier0_post:
            pre_val = int(pre_counts.get(db_key, 0))
            post_val = int(db_tier0_post.get(db_key, 0))
            if post_val < pre_val:
                db_sovereignty_ok = False
                failures.append(f"{db_key} dropped: {pre_val} -> {post_val}")
        checks["tier0_db_sovereignty_preserved"] = db_sovereignty_ok

    sqlite_ok = True
    stale_db_rows = 0
    check_prefixes = stale_prefixes or _stale_path_prefixes_for_vault(vault_root)
    eng_prefixes = _stale_engine_dir_prefixes(check_prefixes)
    if db_path.is_file():
        try:
            con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                qc = con.execute("PRAGMA quick_check(1)").fetchone()
                sqlite_ok = bool(qc and str(qc[0]).lower() == "ok")
                if sqlite_ok and check_healed_paths:
                    has_papers = con.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='papers'"
                    ).fetchone()
                    if has_papers:
                        for row in con.execute(
                            "SELECT ocr_md_path, ocr_json_path, fulltext_path FROM papers"
                        ).fetchall():
                            for val in row:
                                s = str(val or "")
                                if any(p in s for p in eng_prefixes):
                                    stale_db_rows += 1
            finally:
                con.close()
        except sqlite3.Error:
            sqlite_ok = False
    checks["sqlite_integrity"] = sqlite_ok
    if not sqlite_ok:
        failures.append("paperforge.db failed PRAGMA quick_check")

    bases_ok = True
    if base_root and base_root.is_dir():
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            yaml = None
        for bf in base_root.glob("*.base"):
            txt = bf.read_text(encoding="utf-8", errors="ignore")
            if not _is_paperforge_owned_base_file(txt, bf, known_domains):
                continue
            if yaml is not None:
                try:
                    parsed = yaml.safe_load(txt)
                    if not isinstance(parsed, dict) or "views" not in parsed:
                        bases_ok = False
                        failures.append(f"invalid base schema: {bf.name}")
                except Exception as exc:  # noqa: BLE001
                    bases_ok = False
                    failures.append(f"base yaml parse error in {bf.name}: {exc}")
    checks["bases_yaml_valid"] = bases_ok

    if check_healed_paths:
        no_stale_db = stale_db_rows == 0
        checks["no_stale_db_paths"] = no_stale_db
        if not no_stale_db:
            failures.append(f"{stale_db_rows} stale engine path values remain in paperforge.db")

        stale_meta_left = 0
        for ws in scan.workspaces.values():
            meta = ws.paper_meta or {}
            for fld in ("ocr_md_path", "ocr_json_path", "fulltext_path"):
                if any(p in str(meta.get(fld) or "") for p in check_prefixes):
                    stale_meta_left += 1
                    break
        checks["no_stale_paper_meta_paths"] = stale_meta_left == 0
        if stale_meta_left > 0:
            failures.append(f"{stale_meta_left} paper-meta.json file(s) still contain stale prefixes")

    return {
        "ok": len(failures) == 0,
        "checks": checks,
        "counts": post_counts,
        "failures": failures,
    }


def heal_vault_progressive(
    vault: Path,
    *,
    limit: int | None = None,
    priority_key: str | None = None,
    backfill_ocr: bool = False,
    scan: Any | None = None,
    run_reconcile: bool = True,
    run_verify: bool = True,
    out_scan: list[Any] | None = None,
) -> dict[str, Any]:
    """Non-blocking background / JIT healing pass with Skip-and-Isolate error tolerance.

    Processes up to *limit* workspaces (prioritizing *priority_key* first when a
    researcher opens an unhealed paper), runs OCR Tier-0 -> Tier-1 local backfill
    BEFORE verifying workspace fulltext mirrors, cleans stale `paper-meta.json`
    strings, materializes visual assets, quarantines verified legacy flat notes,
    preserves backlink aliases on note renames, reconciles DB/index paths, and
    verifies zero stale engine paths remain.
    """
    from paperforge.config import ConfigError, load_config, resolve_paths
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.storage_migration import rewrite_visual_embeds_for_key
    from paperforge.services.vault_engine import (
        VaultOperationLock,
        quarantine_move,
        read_vault_manifest,
        sync_ocr_catalog,
        sync_workspace_registry,
        write_vault_manifest,
    )
    from paperforge.worker.asset_index import (
        cleanup_or_preserve_workspace_fulltext,
        sync_workspace_visual_assets,
    )

    vault_root = Path(vault).expanduser().resolve()
    with VaultOperationLock(vault_root, operation="upgrade.heal", timeout=0.0, create_dir=True):
        return _heal_vault_progressive_locked(
            vault_root,
            limit=limit,
            priority_key=priority_key,
            backfill_ocr=backfill_ocr,
            scan=scan,
            run_reconcile=run_reconcile,
            run_verify=run_verify,
            out_scan=out_scan,
        )


def _heal_vault_progressive_locked(
    vault_root: Path,
    *,
    limit: int | None = None,
    priority_key: str | None = None,
    backfill_ocr: bool = False,
    scan: Any | None = None,
    run_reconcile: bool = True,
    run_verify: bool = True,
    out_scan: list[Any] | None = None,
) -> dict[str, Any]:
    from paperforge.config import ConfigError, load_config, resolve_paths
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.storage_migration import rewrite_visual_embeds_for_key
    from paperforge.services.vault_engine import (
        quarantine_move,
        read_vault_manifest,
        sync_ocr_catalog,
        sync_workspace_registry,
        write_vault_manifest,
    )
    from paperforge.worker.asset_index import (
        cleanup_or_preserve_workspace_fulltext,
        sync_workspace_visual_assets,
    )

    configured_sys = ""
    try:
        snap = load_config(vault_root)
        configured_sys = str(snap.values["system_dir"].value or "")
        paths = resolve_paths(vault_root, snap)
    except ConfigError:
        raw_cfg: dict[str, Any] = {}
        cfg_p = vault_root / "paperforge.json"
        if cfg_p.is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
                parsed = json.loads(cfg_p.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    raw_cfg = parsed
        raw_layout = _resolve_layout_from_raw(vault_root, raw_cfg)
        configured_sys = raw_layout["system_dir"]
        paths = {
            "vault": vault_root,
            "literature": raw_layout["literature"],
            "paperforge": vault_root / ".paperforge",
            "ocr": vault_root / ".paperforge" / "ocr",
        }

    stale_prefixes = _stale_path_prefixes_for_vault(vault_root, configured_sys)
    lit_root = paths.get("literature")
    ocr_root = paths.get("ocr") or (vault_root / ".paperforge" / "ocr")
    processed = 0
    meta_cleaned = 0
    notes_renamed = 0
    assets_synced = 0
    backfilled = 0
    flat_notes_quarantined = 0
    skipped_isolated: list[dict[str, str]] = []

    # 1. Run local zero-cost OCR backfill BEFORE workspace fulltext cleanup so
    # unmodified workspace mirrors still match the rebuilt OCR fulltext hash.
    if backfill_ocr and safe_is_dir(ocr_root):
        from paperforge.worker.ocr_rebuild import backfill_from_result

        ocr_dirs = [d for d in safe_iterdir(ocr_root) if safe_is_dir(d)]
        if priority_key and safe_is_dir(ocr_root / priority_key):
            ocr_dirs = [ocr_root / priority_key] + [d for d in ocr_dirs if d.name != priority_key]
        if limit is not None and limit > 0:
            ocr_dirs = ocr_dirs[:limit]
        for pdir in ocr_dirs:
            atom = assess_ocr_bundle_atoms(pdir, fast=True)
            if atom["salvage_action"] not in ("backfill_from_result_json", "rebuild_derived_local"):
                continue
            bk = atom["zotero_key"]
            try:
                res_json = pdir / "json" / "result.json"
                if safe_is_file(res_json):
                    bak = pdir / "json" / "result.json.pre-backfill.bak"
                    if not bak.exists():
                        shutil.copy2(str(res_json), str(bak))
                bres = backfill_from_result(vault_root, bk)
                if bres.get("backfill_status") == "done":
                    backfilled += 1
                else:
                    skipped_isolated.append({"key": bk, "reason": str(bres.get("error") or bres.get("backfill_status"))})
            except Exception as exc:  # noqa: BLE001
                skipped_isolated.append({"key": bk, "reason": str(exc)})

    scan = scan if scan is not None else scan_vault_identities(lit_root)
    if lit_root and safe_is_dir(lit_root):
        ordered_keys = sorted(scan.workspaces.keys())
        if priority_key and priority_key in scan.workspaces:
            ordered_keys = [priority_key] + [k for k in ordered_keys if k != priority_key]
        if limit is not None and limit > 0:
            ordered_keys = ordered_keys[:limit]

        for key in ordered_keys:
            ws = scan.workspaces[key]
            try:
                if ws.paper_meta_path is not None and _strip_stale_paper_meta_paths(
                    ws.paper_meta_path, stale_prefixes=stale_prefixes
                ):
                    meta_cleaned += 1

                canonical_note = ws.workspace_dir / f"{key}.md"
                old_note: Path | None = None
                if not canonical_note.exists():
                    if (
                        ws.main_note_path is not None
                        and ws.main_note_path != canonical_note
                        and ws.main_note_path.stem.startswith(f"{key} - ")
                    ):
                        old_note = ws.main_note_path
                    elif len(ws.legacy_named_notes) == 1:
                        old_note = ws.legacy_named_notes[0]
                if old_note is not None and safe_is_file(old_note):
                    old_stem = unicodedata.normalize("NFC", old_note.stem)
                    shutil.move(str(old_note), str(canonical_note))
                    _inject_backlink_alias(canonical_note, old_stem)
                    ws.main_note_path = canonical_note
                    notes_renamed += 1

                p_ocr = ocr_root / key
                if safe_is_dir(p_ocr):
                    copied = sync_workspace_visual_assets(p_ocr, ws.workspace_dir, key)
                    assets_synced += len(copied)
                    note_target = canonical_note if safe_is_file(canonical_note) else ws.main_note_path
                    if note_target and safe_is_file(note_target):
                        orig_txt = note_target.read_text(encoding="utf-8")
                        ws_assets = ws.workspace_dir / "assets"
                        avail_assets: set[str] | None = None
                        if safe_is_dir(ws_assets):
                            avail_assets = {
                                p.name
                                for p in safe_iterdir(ws_assets)
                                if safe_is_file(p) and p.suffix.lower() == ".jpg"
                            }
                        elif safe_is_dir(p_ocr / "assets"):
                            avail_assets = set()
                        updated_txt, r_cnt = rewrite_visual_embeds_for_key(
                            orig_txt, key, available_assets=avail_assets
                        )
                        if r_cnt > 0 and (
                            "render/" in orig_txt or (safe_is_dir(ws_assets) and safe_iterdir(ws_assets))
                        ):
                            write_text_atomic(note_target, updated_txt)
                    if ws.has_workspace_fulltext:
                        cleanup_or_preserve_workspace_fulltext(
                            ws.workspace_dir,
                            vault=vault_root,
                            ocr_paper_dir=p_ocr,
                            lit_root=lit_root,
                            paper_key=key,
                            dry_run=False,
                        )
                processed += 1
            except Exception as exc:  # noqa: BLE001 — Skip & Isolate: 1 weird paper never blocks others
                skipped_isolated.append({"key": key, "reason": str(exc)})

        # Quarantine Four-Gate verified legacy flat notes whose workspace exists
        if scan.flat_notes and (limit is None or limit <= 0):
            for flat in scan.flat_notes:
                if flat.classification != "verified_legacy_flat":
                    continue
                ws_match = scan.workspaces.get(flat.zotero_key)
                if ws_match is None or ws_match.main_note_path is None or not ws_match.main_note_path.is_file():
                    continue
                try:
                    rec = quarantine_move(
                        flat.note_path,
                        vault=vault_root,
                        allowed_root=lit_root,
                        operation="upgrade_clean_legacy_flat",
                        paper_key=flat.zotero_key,
                    )
                    if rec is not None:
                        flat_notes_quarantined += 1
                except Exception as exc:  # noqa: BLE001
                    skipped_isolated.append({"key": flat.zotero_key, "reason": f"flat_cleanup: {exc}"})

    # Re-scan after renames / flat cleanup when reconciling DB
    final_scan = scan_vault_identities(lit_root) if (notes_renamed or flat_notes_quarantined) else scan
    if out_scan is not None:
        out_scan.clear()
        out_scan.append(final_scan)
    reconcile_res = _reconcile_db_and_index_after_cutover(vault_root, final_scan, stale_prefixes)
    reg_res = sync_workspace_registry(vault_root, lit_root=lit_root, scan=final_scan)
    ocr_res = sync_ocr_catalog(vault_root)
    epoch_reconcile: dict[str, Any] | None = None
    if run_reconcile and (limit is None or limit <= 0):
        try:
            from paperforge.services.upgrade_reconcile import ensure_vault_reconciled

            epoch_reconcile = ensure_vault_reconciled(vault_root, force=True, scan=final_scan)
        except Exception as exc:  # noqa: BLE001
            skipped_isolated.append({"key": "_reconcile_epoch", "reason": str(exc)})
    if (limit is None or limit <= 0) and read_vault_manifest(vault_root) is not None:
        with contextlib.suppress(Exception):
            write_vault_manifest(vault_root, heal_pending=False)
    verify_res = (
        verify_vault_upgrade(
            vault_root,
            stale_prefixes=stale_prefixes,
            check_healed_paths=(limit is None or limit <= 0),
            scan=final_scan,
        )
        if run_verify
        else None
    )
    return {
        "processed_workspaces": processed,
        "paper_meta_cleaned": meta_cleaned,
        "legacy_notes_renamed": notes_renamed,
        "visual_assets_synced": assets_synced,
        "ocr_backfilled": backfilled,
        "flat_notes_quarantined": flat_notes_quarantined,
        "db_paths_updated": reconcile_res["db_paths_updated"],
        "sidecars_hydrated": reconcile_res["sidecars_hydrated"],
        "workspace_registry_upserted": reg_res["upserted"],
        "ocr_catalog_total": ocr_res["total"],
        "skipped_isolated": skipped_isolated,
        "reconcile_epoch": epoch_reconcile,
        "verification": verify_res,
    }


def execute_vault_upgrade(
    vault: Path,
    *,
    dry_run: bool = True,
    fast_cutover: bool = False,
    backfill_ocr: bool = False,
    quarantine_residuals: bool = False,
    quarantine_ids: list[str] | None = None,
    rebuild_db: bool = True,
    zotero_source_mode: str | None = None,
    zotero_selected_collections: str | None = None,
    zotero_data_dir: str | None = None,
) -> dict[str, Any]:
    """Execute safe vault upgrade (`fast_cutover=True` for <3s UI cutover, or full pass)."""
    from paperforge.config import ConfigError, load_config, migrate_config, resolve_paths, set_config, validate_config
    from paperforge.services.migration_contract import UpgradePhase, UpgradeStateMachine
    from paperforge.services.storage_migration import (
        _move_tree_entries,
        migrate_vault_storage,
        quiesce_sqlite_wal,
    )
    from paperforge.services.vault_engine import VaultOperationLock, quarantine_move, write_vault_manifest
    from paperforge.worker import load_domain_config
    from paperforge.worker.base_views import ensure_base_views

    vault_root = Path(vault).expanduser().resolve()
    fsm = UpgradeStateMachine()
    plan = inspect_vault_upgrade(
        vault_root,
        fast_summary=(not dry_run and not quarantine_residuals and quarantine_ids is None),
    )
    if dry_run:
        return {
            "dry_run": True,
            "applied": False,
            "plan": plan,
            "executed_steps": [],
            "errors": [],
            "fsm": fsm.to_dict(),
        }

    with VaultOperationLock(vault_root, operation="upgrade.cutover", timeout=0.0, create_dir=True):
        return _execute_vault_upgrade_locked(
            vault_root,
            fsm=fsm,
            plan=plan,
            fast_cutover=fast_cutover,
            backfill_ocr=backfill_ocr,
            quarantine_residuals=quarantine_residuals,
            quarantine_ids=quarantine_ids,
            rebuild_db=rebuild_db,
            zotero_source_mode=zotero_source_mode,
            zotero_selected_collections=zotero_selected_collections,
            zotero_data_dir=zotero_data_dir,
        )


def _execute_vault_upgrade_locked(
    vault_root: Path,
    *,
    fsm: Any,
    plan: dict[str, Any],
    fast_cutover: bool,
    backfill_ocr: bool,
    quarantine_residuals: bool,
    quarantine_ids: list[str] | None,
    rebuild_db: bool,
    zotero_source_mode: str | None = None,
    zotero_selected_collections: str | None = None,
    zotero_data_dir: str | None = None,
) -> dict[str, Any]:
    from paperforge.config import ConfigError, load_config, migrate_config, resolve_paths, set_config, validate_config
    from paperforge.services.migration_contract import UpgradePhase
    from paperforge.services.storage_migration import (
        _move_tree_entries,
        migrate_vault_storage,
        quiesce_sqlite_wal,
    )
    from paperforge.services.vault_engine import quarantine_move, write_vault_manifest
    from paperforge.worker import load_domain_config
    from paperforge.worker.base_views import ensure_base_views

    fsm.transition(UpgradePhase.PREFLIGHT_AUDIT, gate="G0_preflight")
    blocking_ids = {"config.corrupt_json", "db.file_locked"}
    blockers = [t for t in plan["category_c_tamper"] if t["id"] in blocking_ids]
    if blockers:
        fsm.transition(
            UpgradePhase.ABORTED_CLEAN,
            gate="G0_preflight_blocker",
            detail=[b["id"] for b in blockers],
        )
        return {
            "dry_run": False,
            "applied": False,
            "status": "failed",
            "plan": plan,
            "executed_steps": [],
            "errors": [{"step": "preflight_blocker", "error": b["title"]} for b in blockers],
            "fsm": fsm.to_dict(),
        }

    # Resolve configured system_dir & base_dir accurately (including 99_System & custom base_dir!)
    cfg_sys = "System"
    cfg_base = "Bases"
    pre_lit_root: Path | None = None
    try:
        snap = load_config(vault_root)
        cfg_sys = str(snap.values["system_dir"].value or "System")
        cfg_base = str(snap.values["base_dir"].value or "Bases")
        pre_lit_root = resolve_paths(vault_root, snap)["literature"]
    except ConfigError:
        raw_c: dict[str, Any] = {}
        if (vault_root / "paperforge.json").is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                parsed_c = json.loads((vault_root / "paperforge.json").read_text(encoding="utf-8"))
                if isinstance(parsed_c, dict):
                    raw_c = parsed_c
        raw_layout = _resolve_layout_from_raw(vault_root, raw_c)
        cfg_sys = raw_layout["system_dir"]
        cfg_base = raw_layout["base_dir"]
        pre_lit_root = raw_layout["literature"]

    legacy_pf = _detect_legacy_engine_root(vault_root, cfg_sys)
    engine_root = (
        vault_root / ".paperforge"
        if (vault_root / ".paperforge" / "indexes").exists()
        else legacy_pf or (vault_root / ".paperforge")
    )

    req_headroom = 32 * 1024 * 1024
    db_sz = 0
    for db_probe in (engine_root / "indexes" / "paperforge.db", vault_root / ".paperforge" / "indexes" / "paperforge.db"):
        if safe_is_file(db_probe):
            with contextlib.suppress(OSError):
                db_sz = max(db_sz, int(db_probe.stat().st_size))
    req_headroom = max(req_headroom, db_sz // 2 + 32 * 1024 * 1024)
    if legacy_pf is not None:
        with contextlib.suppress(OSError):
            if legacy_pf.stat().st_dev != vault_root.stat().st_dev:
                req_headroom = max(req_headroom, _dir_or_file_bytes(legacy_pf))

    ok_space, free_bytes = _check_disk_headroom(vault_root, req_headroom)
    if not ok_space:
        fsm.transition(UpgradePhase.ABORTED_CLEAN, gate="G0_disk_space", detail={"free_bytes": free_bytes, "required_bytes": req_headroom})
        return {
            "dry_run": False,
            "applied": False,
            "status": "failed",
            "plan": plan,
            "executed_steps": [],
            "errors": [{"step": "disk_space", "error": f"Insufficient disk space ({free_bytes} bytes free)"}],
            "fsm": fsm.to_dict(),
        }

    for db_cand in (engine_root / "indexes" / "paperforge.db", vault_root / ".paperforge" / "indexes" / "paperforge.db"):
        if safe_is_file(db_cand):
            ok_q = quiesce_sqlite_wal(db_cand)
            if not ok_q:
                wal_cand = Path(f"{db_cand}-wal")
                has_dirty_wal = False
                if safe_is_file(wal_cand):
                    with contextlib.suppress(OSError):
                        has_dirty_wal = wal_cand.stat().st_size > 0
                if has_dirty_wal:
                    fsm.transition(UpgradePhase.ABORTED_CLEAN, gate="G1_wal_quiesce", detail={"db": str(db_cand)})
                    return {
                        "dry_run": False,
                        "applied": False,
                        "status": "failed",
                        "plan": plan,
                        "executed_steps": [],
                        "errors": [{"step": "wal_quiesce", "error": f"Cannot quiesce active WAL before upgrade: {db_cand.name}"}],
                        "fsm": fsm.to_dict(),
                    }

    fsm.transition(UpgradePhase.SNAPSHOT_AND_QUIESCE, gate="G1_snapshot")
    backup_dir = _snapshot_preflight_backups(vault_root, engine_root, cfg_sys, configured_base_dir=cfg_base)
    stale_prefixes = _stale_path_prefixes_for_vault(vault_root, cfg_sys)
    pre_scan = None
    if not fast_cutover:
        from paperforge.services.identity_resolver import scan_vault_identities

        pre_scan = scan_vault_identities(pre_lit_root)
    pre_counts = _capture_pre_upgrade_counts(
        vault_root, engine_root, pre_lit_root, fast_mode=fast_cutover, scan=pre_scan
    )

    executed_steps: list[dict[str, Any]] = [{"step": "preflight_backup", "backup_dir": str(backup_dir)}]
    errors: list[dict[str, str]] = []

    fsm.transition(UpgradePhase.ENGINE_CUTOVER, gate="G1_cutover_start")

    # 1. Config schema v2 migration (or bootstrap rescue vault missing paperforge.json)
    cfg_path = vault_root / "paperforge.json"
    if not cfg_path.is_file():
        try:
            from paperforge.config import bootstrap_config

            bootstrap_config(vault_root)
            if safe_is_dir(vault_root / "03_Resources" / "Literature") and not safe_is_dir(
                vault_root / "Resources" / "Literature"
            ):
                set_config(vault_root, "resources_dir", "03_Resources")
            if safe_is_dir(vault_root / "05_Bases") and not safe_is_dir(vault_root / "Bases"):
                set_config(vault_root, "base_dir", "05_Bases")
            set_config(vault_root, "system_dir", ".paperforge")
            executed_steps.append({"step": "config_rescue_bootstrap", "ok": True})
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "config_rescue_bootstrap", "error": str(exc)})
    elif validate_config(vault_root).state == "migration_required":
        try:
            mres = migrate_config(vault_root, dry_run=False)
            executed_steps.append({"step": "config_migrate", "changed": mres.changed, "warnings": list(mres.warnings)})
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "config_migrate", "error": str(exc)})

    # 2. Storage layout migration (`System/PaperForge` or `99_System/PaperForge` -> `.paperforge`)
    legacy_pf = _detect_legacy_engine_root(vault_root, cfg_sys)
    if legacy_pf is not None:
        try:
            if fast_cutover:
                # O(1) directory rename/merge with real-time rollback journaling
                moved_pairs: list[tuple[Path, Path]] = []
                target_pf = vault_root / ".paperforge"
                conflict_dir = target_pf / "backups" / "storage-migration"
                journal_path = target_pf / ".migration-journal.json"

                def _flush_fast_journal(state_val: str = "in_progress") -> None:
                    serialized_pairs = [{"src": str(s), "dst": str(d)} for s, d in moved_pairs]
                    write_json_atomic(backup_dir / "moved-pairs.json", serialized_pairs)
                    write_json_atomic(
                        journal_path,
                        {
                            "state": state_val,
                            "mode": "fast_cutover",
                            "source_engine_dir": str(legacy_pf),
                            "target_engine_dir": str(target_pf),
                            "previous_system_dir": cfg_sys,
                            "moved_pairs": serialized_pairs,
                        },
                    )

                _flush_fast_journal("in_progress")
                try:
                    t_counts = _move_tree_entries(
                        legacy_pf,
                        target_pf,
                        dry_run=False,
                        moved_pairs=moved_pairs,
                        conflict_backup_dir=conflict_dir,
                        on_progress=lambda: _flush_fast_journal("in_progress"),
                    )
                    if (vault_root / "paperforge.json").is_file():
                        set_config(vault_root, "system_dir", ".paperforge")
                except Exception:
                    with contextlib.suppress(OSError):
                        _flush_fast_journal("in_progress")
                    raise
                _flush_fast_journal("completed")
                with contextlib.suppress(OSError):
                    if safe_is_dir(legacy_pf) and not safe_iterdir(legacy_pf):
                        legacy_pf.rmdir()
                    if safe_is_dir(legacy_pf.parent) and legacy_pf.parent != vault_root and not safe_iterdir(legacy_pf.parent):
                        legacy_pf.parent.rmdir()
                executed_steps.append({"step": "fast_storage_cutover", "result": t_counts})
            else:
                sres = migrate_vault_storage(
                    vault_root,
                    dry_run=False,
                    isolate_paper_errors=True,
                    backup_dir=backup_dir,
                    scan=pre_scan,
                )
                executed_steps.append({"step": "storage_migration", "result": sres})
                for pe in sres.get("paper_errors") or []:
                    errors.append(
                        {
                            "step": f"storage_migration:{pe.get('key', 'unknown')}",
                            "error": str(pe.get("error") or "paper migration error"),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "storage_migration", "error": str(exc)})
    elif (vault_root / "paperforge.json").is_file() and cfg_sys != ".paperforge":
        with contextlib.suppress(Exception):
            set_config(vault_root, "system_dir", ".paperforge")

    # G2 mid-flight DB / OCR sovereignty check (skip workspace rescan — G2 only checks OCR & SQLite invariants)
    cutover_failed = any(e.get("step") == "storage_migration" for e in errors)
    if not cutover_failed:
        post_cutover_counts = _capture_pre_upgrade_counts(
            vault_root,
            vault_root / ".paperforge",
            pre_lit_root,
            fast_mode=fast_cutover,
            skip_workspace_scan=True,
        )
        g2_failures: list[str] = []
        if post_cutover_counts["tier0_ocr_valid"] < pre_counts["tier0_ocr_valid"]:
            g2_failures.append(
                f"tier0_ocr_valid dropped at G2: {pre_counts['tier0_ocr_valid']} -> {post_cutover_counts['tier0_ocr_valid']}"
            )
        for db_key, _ in _DB_TIER0_TABLE_MAP:
            pre_v = int(pre_counts.get(db_key, 0))
            post_v = int(post_cutover_counts.get(db_key, 0))
            if post_v < pre_v:
                g2_failures.append(f"{db_key} dropped at G2: {pre_v} -> {post_v}")
        if g2_failures:
            fsm.transition(UpgradePhase.SOVEREIGNTY_VIOLATION, gate="G2_mid_flight_sovereignty", detail=g2_failures)
            fsm.transition(UpgradePhase.ROLLING_BACK, gate="G2_auto_rollback")
            rb_res = rollback_vault_upgrade(vault_root, backup_dir=backup_dir)
            fsm.transition(
                UpgradePhase.ROLLED_BACK,
                gate="G2_rolled_back",
                detail={"rolled_back": bool(rb_res.get("rolled_back"))},
            )
            fsm.persist(backup_dir / "fsm-trace.json")
            return {
                "dry_run": False,
                "applied": False,
                "status": "rolled_back",
                "mode": "fast_cutover" if fast_cutover else "full",
                "backup_dir": str(backup_dir),
                "executed_steps": executed_steps,
                "errors": errors + [{"step": "g2_sovereignty", "error": "; ".join(g2_failures)}],
                "rollback": rb_res,
                "fsm": fsm.to_dict(),
            }

    fsm.transition(UpgradePhase.DERIVED_VIEW_AND_INDEX_RECONCILE, gate="G2_passed")

    # 3. Resolve post-cutover paths & upgrade ONLY PaperForge-owned Base views
    try:
        paths = resolve_paths(vault_root)
    except ConfigError:
        paths = {
            "vault": vault_root,
            "literature": pre_lit_root or (vault_root / "Resources" / "Literature"),
            "bases": vault_root / cfg_base,
            "paperforge": vault_root / ".paperforge",
            "exports": vault_root / ".paperforge" / "exports",
            "config": vault_root / ".paperforge" / "config" / "domain-collections.json",
            "ocr": vault_root / ".paperforge" / "ocr",
        }

    try:
        exports_dir = paths.get("exports") or (vault_root / ".paperforge" / "exports")
        domain_cfg = load_domain_config(paths) if safe_is_dir(exports_dir) else {"schema_version": 1, "domains": []}
        # Also include any PaperForge-owned `.base` files already present in `Bases/`
        existing_domains = {d.get("domain") for d in domain_cfg.get("domains", [])}
        base_dir = paths.get("bases")
        if base_dir and safe_is_dir(base_dir):
            for bf in safe_iterdir(base_dir):
                if bf.suffix.lower() != ".base" or bf.name == "Literature Hub.base":
                    continue
                txt = bf.read_text(encoding="utf-8", errors="ignore")
                if _is_paperforge_owned_base_file(txt, bf, set()) and bf.stem not in existing_domains:
                    domain_cfg.setdefault("domains", []).append(
                        {"domain": bf.stem, "export_file": f"{bf.stem}.json", "allowed_collections": []}
                    )
        if domain_cfg.get("domains") or (base_dir and safe_is_file(base_dir / "Literature Hub.base")):
            ensure_base_views(vault_root, paths, domain_cfg)
        executed_steps.append({"step": "base_views_upgrade", "ok": True})
    except Exception as exc:  # noqa: BLE001
        errors.append({"step": "base_views_upgrade", "error": str(exc)})

    # 5. Confirmed residual quarantine (supports selective `quarantine_ids`)
    selected_ids: set[str] | None = None
    if quarantine_ids is not None:
        selected_ids = set(quarantine_ids)
    elif quarantine_residuals:
        selected_ids = {str(c["id"]) for c in plan["cleanup_candidates"]}

    if selected_ids:
        quarantined_count = 0
        legacy_pf_abs = Path(os.path.abspath(str(legacy_pf))) if legacy_pf is not None else None
        dot_pf_root = vault_root / ".paperforge"
        for cand in plan["cleanup_candidates"]:
            if cand["id"] not in selected_ids:
                continue
            target_p = Path(cand["path"])
            if not target_p.exists() and legacy_pf_abs is not None:
                cand_abs = Path(os.path.abspath(str(target_p)))
                if cand_abs.is_relative_to(legacy_pf_abs):
                    remapped = dot_pf_root / cand_abs.relative_to(legacy_pf_abs)
                    if remapped.exists():
                        target_p = remapped
            if not target_p.exists():
                continue
            try:
                rec = quarantine_move(
                    target_p,
                    vault=vault_root,
                    allowed_root=vault_root,
                    operation=f"upgrade_quarantine:{cand['id']}",
                )
                if rec is not None:
                    quarantined_count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({"step": f"quarantine:{cand['id']}", "error": str(exc)})
        executed_steps.append({"step": "quarantine_residuals", "quarantined": quarantined_count})

    # 6. Best-effort sync of machine Skill Hub & registered agent installs (Zero Vault Pollution)
    try:
        from paperforge.services.skill_deploy import sync_machine_skill_hub, sync_registered_agent_skills

        sync_machine_skill_hub()
        sync_registered_agent_skills()
        executed_steps.append({"step": "skill_hub_sync", "ok": True})
    except Exception as exc:  # noqa: BLE001
        logger.debug("best-effort skill sync skipped: %s", exc)

    # 7. Atomically commit confirmed Zotero configuration (if supplied) BEFORE stamping manifest
    zotero_commit_failed = False
    if not cutover_failed and (
        zotero_source_mode is not None
        or zotero_selected_collections is not None
        or zotero_data_dir is not None
    ):
        try:
            if zotero_data_dir is not None and zotero_data_dir.strip():
                set_config(vault_root, "zotero_data_dir", zotero_data_dir.strip())
            if zotero_source_mode is not None and zotero_source_mode.strip():
                set_config(vault_root, "zotero_source_mode", zotero_source_mode.strip())
            if zotero_selected_collections is not None:
                set_config(vault_root, "zotero_selected_collections", zotero_selected_collections)
            executed_steps.append(
                {
                    "step": "zotero_config_commit",
                    "mode": zotero_source_mode,
                    "selected_collections": zotero_selected_collections,
                }
            )
        except Exception as exc:  # noqa: BLE001
            zotero_commit_failed = True
            errors.append({"step": "zotero_config_commit", "error": str(exc)})

    # 8. Stamp `.paperforge/vault-manifest.json` with rollback reference
    manifest_written = False
    if not zotero_commit_failed and not cutover_failed:
        try:
            sync_pending = bool(
                fast_cutover
                or zotero_source_mode is not None
                or zotero_selected_collections is not None
            )
            manifest_path = write_vault_manifest(
                vault_root,
                migration_entry={
                    "timestamp": _utcnow_compact(),
                    "mode": "fast_cutover" if fast_cutover else "full",
                    "status": "partial_success" if errors else "completed",
                    "backup_dir": str(backup_dir),
                    "steps": [s["step"] for s in executed_steps],
                    "error_count": len(errors),
                },
                heal_pending=bool(fast_cutover),
                post_upgrade_sync_pending=sync_pending,
            )
            manifest_written = True
            executed_steps.append({"step": "write_vault_manifest", "path": str(manifest_path)})
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "write_vault_manifest", "error": str(exc)})

    # 9. Stamp reconcile_epoch once (in fast_cutover here; in full mode inside progressive_heal on final workspaces)
    heal_scan_box: list[Any] = []
    if fast_cutover:
        if manifest_written and not cutover_failed and not zotero_commit_failed:
            try:
                from paperforge.services.upgrade_reconcile import ensure_vault_reconciled

                rec_res = ensure_vault_reconciled(vault_root, force=True)
                executed_steps.append({"step": "upgrade_reconcile", "result": rec_res})
            except Exception as exc:  # noqa: BLE001
                errors.append({"step": "upgrade_reconcile", "error": str(exc)})
    else:
        # 4. Progressive healing (immediate in full mode; deferred to background daemon in fast_cutover mode)
        fsm.transition(UpgradePhase.PER_WORKSPACE_PROGRESSIVE_HEAL, gate="G3_progressive_heal")
        step_name = "progressive_heal" if rebuild_db else "workspace_normalize"
        try:
            heal_res = heal_vault_progressive(
                vault_root,
                backfill_ocr=backfill_ocr,
                scan=pre_scan,
                run_reconcile=True,
                run_verify=False,
                out_scan=heal_scan_box,
            )
            executed_steps.append({"step": step_name, "result": heal_res})
            if heal_res.get("reconcile_epoch") is not None:
                executed_steps.append({"step": "upgrade_reconcile", "result": heal_res["reconcile_epoch"]})
            for si in heal_res.get("skipped_isolated") or []:
                errors.append(
                    {
                        "step": f"{step_name}:{si.get('key', 'unknown')}",
                        "error": str(si.get("reason") or "workspace heal skipped"),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": step_name, "error": str(exc)})

    settlement_status = "partial_success" if errors else "completed"

    verification = verify_vault_upgrade(
        vault_root,
        pre_counts=pre_counts,
        stale_prefixes=stale_prefixes,
        check_healed_paths=not fast_cutover,
        fast_mode=fast_cutover,
        scan=heal_scan_box[0] if heal_scan_box else None,
    )

    if not cutover_failed and (
        verification["checks"].get("tier0_ocr_preserved") is False
        or verification["checks"].get("tier0_db_sovereignty_preserved") is False
        or verification["checks"].get("sidecars_preserved") is False
    ):
        fsm.transition(
            UpgradePhase.SOVEREIGNTY_VIOLATION,
            gate="G4_final_verify",
            detail=verification["failures"],
        )
        fsm.transition(UpgradePhase.ROLLING_BACK, gate="G4_auto_rollback")
        rb_res = rollback_vault_upgrade(vault_root, backup_dir=backup_dir)
        fsm.transition(
            UpgradePhase.ROLLED_BACK,
            gate="G4_rolled_back",
            detail={"rolled_back": bool(rb_res.get("rolled_back"))},
        )
        fsm.persist(backup_dir / "fsm-trace.json")
        return {
            "dry_run": False,
            "applied": False,
            "status": "rolled_back",
            "mode": "fast_cutover" if fast_cutover else "full",
            "backup_dir": str(backup_dir),
            "executed_steps": executed_steps,
            "errors": errors + [{"step": "g4_sovereignty", "error": "; ".join(verification["failures"])}],
            "rollback": rb_res,
            "verification": verification,
            "fsm": fsm.to_dict(),
        }

    terminal_phase = UpgradePhase.COMPLETED_FAST_CUTOVER if fast_cutover else UpgradePhase.COMPLETED
    fsm.transition(terminal_phase, gate="G4_final_verify", detail={"ok": verification["ok"]})
    fsm.persist(backup_dir / "fsm-trace.json")

    return {
        "dry_run": False,
        "applied": True,
        "status": settlement_status,
        "mode": "fast_cutover" if fast_cutover else "full",
        "backup_dir": str(backup_dir),
        "healing_pending": bool(fast_cutover),
        "executed_steps": executed_steps,
        "errors": errors,
        "verification": verification,
        "fsm": fsm.to_dict(),
        "post_check": inspect_vault_upgrade(vault_root, fast_summary=True),
    }


def rollback_vault_upgrade(vault: Path, *, backup_dir: Path | None = None) -> dict[str, Any]:
    """One-Click Time-Machine rollback restoring directory structure, `paperforge.json`, and `.base` files."""
    from paperforge.services.storage_migration import (
        _load_rewritten_notes_for_rollback,
        _move_tree_entries,
        _rollback_mutations,
        _validate_vault_contained_path,
        rollback_incomplete_migration,
    )
    from paperforge.services.vault_engine import VaultOperationLock, vault_manifest_path

    vault_root = Path(vault).expanduser().resolve()
    with VaultOperationLock(vault_root, operation="upgrade.rollback", timeout=0.0, create_dir=False):
        return _rollback_vault_upgrade_locked(vault_root, backup_dir=backup_dir)


def _rollback_vault_upgrade_locked(vault_root: Path, *, backup_dir: Path | None = None) -> dict[str, Any]:
    from paperforge.services.storage_migration import (
        _load_rewritten_notes_for_rollback,
        _move_tree_entries,
        _rollback_mutations,
        _validate_vault_contained_path,
        rollback_incomplete_migration,
    )
    from paperforge.services.vault_engine import vault_manifest_path

    backups_root = vault_root / ".paperforge" / "backups"
    target_snap = backup_dir
    if target_snap is None and backups_root.is_dir():
        snaps = sorted(backups_root.glob("upgrade-*"), reverse=True)
        if snaps:
            target_snap = snaps[0]

    if target_snap is None or not target_snap.is_dir():
        rb = rollback_incomplete_migration(vault_root)
        return {"rolled_back": bool(rb.get("recovered")), "source": "journal", "detail": rb}

    restored_files = 0
    restored_moves = 0

    cutover_meta: dict[str, Any] = {}
    meta_file = target_snap / "cutover-meta.json"
    if meta_file.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
            parsed_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if isinstance(parsed_meta, dict):
                cutover_meta = parsed_meta

    # Reverse fast_cutover moved_pairs or full storage_migration moved_pairs
    raw_pairs: list[dict[str, Any]] = []
    moved_pairs_file = target_snap / "moved-pairs.json"
    journal_file = vault_root / ".paperforge" / ".migration-journal.json"
    if moved_pairs_file.is_file():
        raw_pairs = json.loads(moved_pairs_file.read_text(encoding="utf-8"))
    elif journal_file.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError):
            jdata = json.loads(journal_file.read_text(encoding="utf-8"))
            raw_pairs = list(jdata.get("moved_pairs") or [])

    validated_pairs: list[tuple[Path, Path]] = []
    for item in raw_pairs:
        if not isinstance(item, dict) or not item.get("src") or not item.get("dst"):
            continue
        src_p = _validate_vault_contained_path(item["src"], allowed_root=vault_root, label="rollback.src")
        dst_p = _validate_vault_contained_path(item["dst"], allowed_root=vault_root, label="rollback.dst")
        validated_pairs.append((src_p, dst_p))

    try:
        for src_p, dst_p in reversed(validated_pairs):
            if not dst_p.exists():
                continue
            if not src_p.exists():
                src_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_p), str(src_p))
                restored_moves += 1
            elif dst_p.is_dir() and src_p.is_dir():
                sub_res = _move_tree_entries(dst_p, src_p, dry_run=False)
                restored_moves += int(sub_res.get("moved", 0))
            else:
                raise OSError(f"cannot restore {dst_p} -> {src_p}: destination already exists")
    except OSError as exc:
        # Fail closed BEFORE reverting paperforge.json or archiving vault-manifest.json
        return {
            "rolled_back": False,
            "backup_dir": str(target_snap),
            "restored_moves": restored_moves,
            "restored_files": 0,
            "error": str(exc),
        }

    # Reverse full-migration note/asset/fulltext mutations if recorded
    mut_file = target_snap / "migration-mutations.json"
    if mut_file.is_file():
        with contextlib.suppress(OSError, json.JSONDecodeError, UnicodeDecodeError):
            mut_data = json.loads(mut_file.read_text(encoding="utf-8"))
            if isinstance(mut_data, dict):
                dot_pf_root = (vault_root / ".paperforge").resolve()
                rev_notes = _load_rewritten_notes_for_rollback(
                    list(mut_data.get("rewritten_notes") or []),
                    vault_root=vault_root,
                    dot_pf_root=dot_pf_root,
                    label_prefix="rollback.note",
                )
                rev_assets = [
                    _validate_vault_contained_path(p, allowed_root=vault_root, label="rollback.asset")
                    for p in (mut_data.get("created_assets") or [])
                ]
                rev_fulltexts: list[tuple[Path, bytes]] = []
                for ft_it in (mut_data.get("preserved_fulltexts") or []):
                    if isinstance(ft_it, dict) and ft_it.get("orig") and ft_it.get("backup"):
                        orig_p = _validate_vault_contained_path(
                            ft_it["orig"], allowed_root=vault_root, label="rollback.fulltext.orig"
                        )
                        bak_p = _validate_vault_contained_path(
                            ft_it["backup"], allowed_root=dot_pf_root, label="rollback.fulltext.backup"
                        )
                        if bak_p.is_file():
                            rev_fulltexts.append((orig_p, bak_p.read_bytes()))
                _rollback_mutations(
                    rewritten_notes=rev_notes,
                    restorable_fulltexts=rev_fulltexts,
                    created_assets=rev_assets,
                    moved_pairs=[],
                    config_restorer=None,
                )

    # Restore snapshotted configs and `.base` files (including custom base_dir)
    for rel in ("paperforge.json", ".obsidian/plugins/paperforge/data.json"):
        snap_f = target_snap / rel
        if snap_f.is_file():
            dst_f = vault_root / rel
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(snap_f), str(dst_f))
            restored_files += 1

    # Restore pre-merge permanent JSONL logs if _merge_jsonl_by_id touched them
    jsonl_bak_dir = vault_root / ".paperforge" / "backups" / "storage-migration" / "jsonl_merge"
    if jsonl_bak_dir.is_dir():
        for dst_bak in sorted(jsonl_bak_dir.glob("dst__*")):
            orig_name = dst_bak.name[len("dst__"):]
            if not orig_name or orig_name.startswith("."):
                continue
            prev_sys = str(cutover_meta.get("previous_system_dir") or "").strip()
            target_log = (
                vault_root / prev_sys / "PaperForge" / "logs" / orig_name
                if prev_sys and prev_sys != ".paperforge"
                else vault_root / ".paperforge" / "logs" / orig_name
            )
            cand_dot = vault_root / ".paperforge" / "logs" / orig_name
            log_dst = target_log if target_log.parent.is_dir() else cand_dot
            if log_dst.parent.is_dir():
                with contextlib.suppress(OSError):
                    shutil.copy2(str(dst_bak), str(log_dst))
                    restored_files += 1

    base_subs: list[str] = ["Bases", "05_Bases"]
    for cand_b in list(cutover_meta.get("snapshotted_base_dirs") or []) + [
        str(cutover_meta.get("previous_base_dir") or "").strip()
    ]:
        norm_b = str(cand_b or "").replace("\\", "/").strip().strip("/")
        if norm_b and norm_b not in (".", "..") and norm_b not in base_subs:
            base_subs.append(norm_b)

    seen_base_subs: set[str] = set()
    for base_sub in base_subs:
        if base_sub in seen_base_subs:
            continue
        seen_base_subs.add(base_sub)
        s_bdir = target_snap / base_sub
        if s_bdir.is_dir():
            for bf in s_bdir.glob("*.base"):
                dst_bf = _validate_vault_contained_path(
                    vault_root / base_sub / bf.name,
                    allowed_root=vault_root,
                    label="rollback.base_file",
                )
                dst_bf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(bf), str(dst_bf))
                restored_files += 1

    mf = vault_manifest_path(vault_root)
    if mf.is_file():
        archived = target_snap / "rolled-back-vault-manifest.json"
        shutil.move(str(mf), str(archived))

    if journal_file.is_file():
        write_json_atomic(
            journal_file,
            {
                "state": "rolled_back",
                "reason": "rollback_vault_upgrade",
                "backup_dir": str(target_snap),
                "restored_moves": restored_moves,
                "restored_files": restored_files,
            },
        )

    return {
        "rolled_back": True,
        "backup_dir": str(target_snap),
        "restored_moves": restored_moves,
        "restored_files": restored_files,
    }
