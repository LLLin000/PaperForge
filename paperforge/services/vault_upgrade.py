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
import os
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.core.io import write_json_atomic, write_text_atomic

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


def detect_vault_provenance(vault: Path) -> dict[str, Any]:
    """Classify *vault* into ``standard_current`` | ``veteran_legacy`` | ``veteran_rescue`` | ``fresh_or_foreign``."""
    from paperforge.services.vault_engine import CURRENT_LAYOUT_VERSION, read_vault_manifest

    vault_root = Path(vault).expanduser().resolve()
    manifest = read_vault_manifest(vault_root)
    tier1_evidence: list[str] = []
    tier2_evidence: list[str] = []

    has_legacy_engine = False
    for legacy_cand in (vault_root / "System" / "PaperForge", vault_root / "99_System" / "PaperForge"):
        if legacy_cand.is_dir():
            has_legacy_engine = True
            tier1_evidence.append(f"legacy_engine_dir:{legacy_cand.relative_to(vault_root).as_posix()}")

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
                    tier1_evidence.append(f"configured_legacy_engine:{sys_d}/PaperForge")
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            tier1_evidence.append("paperforge.json:corrupt")

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
    """Non-destructively verify *db_path* is not exclusively locked by another OS process."""
    if not db_path.is_file():
        return True, ""
    try:
        # On Windows, opening r+b catches exclusive OS file locks before moving trees
        with open(db_path, "r+b"):
            pass
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _check_disk_headroom(vault_root: Path, required_bytes: int) -> tuple[bool, int]:
    """Verify at least 2x required_bytes + 64 MB free disk headroom."""
    try:
        free_b = int(shutil.disk_usage(str(vault_root)).free)
    except OSError:
        return True, 0
    needed = max(required_bytes * 2 + 64 * 1024 * 1024, 64 * 1024 * 1024)
    return free_b >= needed, free_b


def _inject_backlink_alias(note_path: Path, old_stem: str) -> None:
    """Preserve `<KEY> - <Title>` inside YAML `aliases` so existing Obsidian `[[wikilinks]]` never break."""
    with contextlib.suppress(OSError, UnicodeDecodeError):
        text = note_path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return
        end_idx = text.find("\n---", 3)
        if end_idx == -1:
            return
        fm_part = text[:end_idx]
        if old_stem in fm_part:
            return
        escaped = old_stem.replace('"', '\\"')
        if re.search(r"^aliases:\s*\[", fm_part, re.MULTILINE):
            new_fm = re.sub(
                r"^(aliases:\s*\[)(.*?)(\]\s*)$",
                lambda m: f'{m.group(1)}{m.group(2)}, "{escaped}"{m.group(3)}' if m.group(2).strip() else f'{m.group(1)}"{escaped}"{m.group(3)}',
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


def _snapshot_preflight_backups(vault_root: Path, engine_root: Path, configured_sys_dir: str) -> Path:
    """Create immutable pre-flight copies of small high-value files before any mutation."""
    snap_dir = vault_root / ".paperforge" / "backups" / f"upgrade-{_utcnow_compact()}"
    snap_dir.mkdir(parents=True, exist_ok=True)
    for rel in (
        "paperforge.json",
        ".env",
        ".obsidian/plugins/paperforge/data.json",
        ".obsidian/plugins/paperforge/manifest.json",
    ):
        src = vault_root / rel
        if src.is_file():
            dst = snap_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
    for base_dir in (vault_root / "Bases", vault_root / "05_Bases"):
        if base_dir.is_dir():
            for bf in base_dir.glob("*.base"):
                dst = snap_dir / bf.relative_to(vault_root)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(bf), str(dst))
    idx_file = engine_root / "indexes" / "formal-library.json"
    if idx_file.is_file():
        shutil.copy2(str(idx_file), str(snap_dir / "formal-library.json"))
    write_json_atomic(
        snap_dir / "cutover-meta.json",
        {
            "created_at": _utcnow_iso(),
            "previous_system_dir": configured_sys_dir,
            "legacy_engine_root": str(engine_root),
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


def inspect_vault_upgrade(vault: Path) -> dict[str, Any]:
    """Read-only Full-Vault Census & A/B/C Upgrade Plan with Five-Bucket Ownership classification."""
    from paperforge import __version__ as PF_VERSION
    from paperforge.config import load_config, paperforge_paths, validate_config
    from paperforge.core.versioning import is_version_compatible
    from paperforge.credentials import CredentialKey, status as cred_status
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.runtime_pointer import read_pointer
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.vault_engine import read_vault_manifest
    from paperforge.worker.base_views import RETIRED_PF_VIEWS

    vault_root = Path(vault).expanduser().resolve()
    provenance = detect_vault_provenance(vault_root)
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
    base_root = vault_root / "Bases"
    zotero_dir_val = ""
    try:
        snap = load_config(vault_root)
        configured_sys_dir = str(snap.values["system_dir"].value or "System")
        configured_skill_dir = str(snap.values["skill_dir"].value or ".agents/skills")
        zotero_dir_val = str(snap.values["zotero_data_dir"].value or "")
        paths = paperforge_paths(vault_root, snap)
        lit_root = paths["literature"]
        base_root = paths["bases"]
    except Exception:  # noqa: BLE001
        vc = cfg_raw.get("vault_config") if isinstance(cfg_raw.get("vault_config"), dict) else {}
        configured_sys_dir = str(vc.get("system_dir") or cfg_raw.get("system_dir") or "System")
        configured_skill_dir = str(vc.get("skill_dir") or cfg_raw.get("skill_dir") or ".opencode/skills")
        zotero_dir_val = str(cfg_raw.get("zotero_data_dir") or "")

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
    scan = scan_vault_identities(lit_root)
    stale_meta_paths: list[Path] = []
    legacy_named_note_count = 0
    ws_fulltext_count = 0
    user_aux_notes_count = 0
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
            if any(prefix in val for prefix in _STALE_PATH_PREFIXES) and ws.paper_meta_path is not None:
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
    if ocr_dir.is_dir():
        for pdir in sorted(d for d in ocr_dir.iterdir() if d.is_dir()):
            atom = assess_ocr_bundle_atoms(pdir)
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
    known_domains = {ws.domain for ws in scan.workspaces.values() if ws.domain}
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
            unquoted_bang = bool(re.search(r"^\s*!zotero_key\.isEmpty\(\)\s*$", txt, re.MULTILINE))
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

    if configured_skill_dir and configured_skill_dir != ".agents/skills":
        reconfig_items.append(
            {
                "id": "skills.non_default_dir",
                "area": "skills",
                "impact": "minor",
                "title": f"AI 技能目录当前设为 {configured_skill_dir}",
                "detail": "继续使用当前工具无需改动；如需多客户端通用可额外部署至 .agents/skills。",
                "remediation": "按需在设置中同步技能。",
            }
        )

    # Database & cleanup candidates
    db_path = engine_root / "indexes" / "paperforge.db"
    if db_path.is_file():
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
            con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            try:
                qc = con.execute("PRAGMA quick_check").fetchone()
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
                    if scan.workspaces and reg_cnt == 0:
                        auto_items.append(
                            {
                                "id": "db.populate_workspace_registry",
                                "area": "database",
                                "title": "填充文献身份高速路由表",
                                "count": len(scan.workspaces),
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
    elif scan.workspaces or ocr_counts["total"] > 0:
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
        for bak in sorted(idx_root.glob("paperforge.db.bak-*")):
            cleanup_candidates.append(
                {
                    "id": f"cleanup.db_bak.{bak.name}",
                    "path": str(bak),
                    "bytes": _dir_or_file_bytes(bak),
                    "reason": "历史数据库恢复快照备份",
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
        "pf_user_enriched": len(scan.workspaces) + len(legacy_bases),
        "pf_confirmed_residual": len(dedup_cleanup),
        "user_sovereign_untouched": user_sovereign_bases + user_aux_notes_count,
        "ambiguous_or_clone_frozen": len(scan.ambiguous_clones) + len(scan.duplicate_workspaces) + len(scan.sync_conflicts),
    }

    return {
        "schema_version": 2,
        "vault": str(vault_root),
        "target_version": PF_VERSION,
        "provenance": provenance,
        "manifest_present": manifest is not None,
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


def _strip_stale_paper_meta_paths(meta_path: Path) -> bool:
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    changed = False
    for field_name in ("ocr_md_path", "ocr_json_path", "fulltext_path"):
        val = str(data.get(field_name) or "")
        if any(prefix in val for prefix in _STALE_PATH_PREFIXES):
            data.pop(field_name, None)
            changed = True
    if changed:
        write_json_atomic(meta_path, data)
    return changed


def heal_vault_progressive(
    vault: Path,
    *,
    limit: int | None = None,
    priority_key: str | None = None,
    backfill_ocr: bool = False,
) -> dict[str, Any]:
    """Non-blocking background / JIT healing pass with Skip-and-Isolate error tolerance.

    Processes up to *limit* workspaces (prioritizing *priority_key* first when a
    researcher opens an unhealed paper), cleans stale `paper-meta.json` strings,
    materializes visual assets, preserves backlink aliases on note renames,
    optionally backfills derived OCR layers from intact `json/result.json`
    (with pre-backfill `result.json` backup), and syncs SQLite SSOT tables.
    """
    from paperforge.config import paperforge_paths
    from paperforge.materialization.ocr import assess_ocr_bundle_atoms
    from paperforge.services.identity_resolver import scan_vault_identities
    from paperforge.services.storage_migration import rewrite_visual_embeds_for_key
    from paperforge.services.vault_engine import sync_ocr_catalog, sync_workspace_registry
    from paperforge.worker.asset_index import (
        cleanup_or_preserve_workspace_fulltext,
        sync_workspace_visual_assets,
    )

    vault_root = Path(vault).expanduser().resolve()
    try:
        paths = paperforge_paths(vault_root)
    except Exception:  # noqa: BLE001
        paths = {
            "vault": vault_root,
            "literature": vault_root / "Resources" / "Literature",
            "paperforge": vault_root / ".paperforge",
            "ocr": vault_root / ".paperforge" / "ocr",
        }

    lit_root = paths.get("literature")
    ocr_root = paths.get("ocr") or (vault_root / ".paperforge" / "ocr")
    processed = 0
    meta_cleaned = 0
    notes_renamed = 0
    assets_synced = 0
    backfilled = 0
    skipped_isolated: list[dict[str, str]] = []

    if lit_root and lit_root.is_dir():
        scan = scan_vault_identities(lit_root)
        ordered_keys = sorted(scan.workspaces.keys())
        if priority_key and priority_key in scan.workspaces:
            ordered_keys = [priority_key] + [k for k in ordered_keys if k != priority_key]
        if limit is not None and limit > 0:
            ordered_keys = ordered_keys[:limit]

        for key in ordered_keys:
            ws = scan.workspaces[key]
            try:
                if ws.paper_meta_path is not None and _strip_stale_paper_meta_paths(ws.paper_meta_path):
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
                if old_note is not None and old_note.is_file():
                    old_stem = unicodedata.normalize("NFC", old_note.stem)
                    shutil.move(str(old_note), str(canonical_note))
                    _inject_backlink_alias(canonical_note, old_stem)
                    notes_renamed += 1

                p_ocr = ocr_root / key
                if p_ocr.is_dir():
                    copied = sync_workspace_visual_assets(p_ocr, ws.workspace_dir, key)
                    assets_synced += len(copied)
                    note_target = canonical_note if canonical_note.is_file() else ws.main_note_path
                    if note_target and note_target.is_file():
                        orig_txt = note_target.read_text(encoding="utf-8")
                        # Only rewrite if it explicitly points to render/ or target asset exists in workspace assets
                        updated_txt, r_cnt = rewrite_visual_embeds_for_key(orig_txt, key)
                        if r_cnt > 0:
                            ws_assets = ws.workspace_dir / "assets"
                            if "render/" in orig_txt or (ws_assets.is_dir() and any(ws_assets.iterdir())):
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

    if backfill_ocr and ocr_root.is_dir():
        from paperforge.worker.ocr_rebuild import backfill_from_result

        ocr_dirs = sorted(d for d in ocr_root.iterdir() if d.is_dir())
        if priority_key and (ocr_root / priority_key).is_dir():
            ocr_dirs = [ocr_root / priority_key] + [d for d in ocr_dirs if d.name != priority_key]
        if limit is not None and limit > 0:
            ocr_dirs = ocr_dirs[:limit]
        for pdir in ocr_dirs:
            atom = assess_ocr_bundle_atoms(pdir)
            if atom["salvage_action"] not in ("backfill_from_result_json", "rebuild_derived_local"):
                continue
            bk = atom["zotero_key"]
            try:
                res_json = pdir / "json" / "result.json"
                if res_json.is_file():
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

    reg_res = sync_workspace_registry(vault_root, lit_root=lit_root)
    ocr_res = sync_ocr_catalog(vault_root)
    return {
        "processed_workspaces": processed,
        "paper_meta_cleaned": meta_cleaned,
        "legacy_notes_renamed": notes_renamed,
        "visual_assets_synced": assets_synced,
        "ocr_backfilled": backfilled,
        "workspace_registry_upserted": reg_res["upserted"],
        "ocr_catalog_total": ocr_res["total"],
        "skipped_isolated": skipped_isolated,
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
) -> dict[str, Any]:
    """Execute safe vault upgrade (`fast_cutover=True` for <3s UI cutover, or full pass)."""
    from paperforge.config import load_config, migrate_config, paperforge_paths, set_config, validate_config
    from paperforge.services.storage_migration import _move_tree_entries, migrate_vault_storage
    from paperforge.services.vault_engine import quarantine_move, write_vault_manifest
    from paperforge.worker import load_domain_config
    from paperforge.worker.base_views import ensure_base_views

    vault_root = Path(vault).expanduser().resolve()
    plan = inspect_vault_upgrade(vault_root)
    if dry_run:
        return {
            "dry_run": True,
            "applied": False,
            "plan": plan,
            "executed_steps": [],
            "errors": [],
        }

    blocking_ids = {"config.corrupt_json", "db.file_locked"}
    blockers = [t for t in plan["category_c_tamper"] if t["id"] in blocking_ids]
    if blockers:
        return {
            "dry_run": False,
            "applied": False,
            "status": "failed",
            "plan": plan,
            "executed_steps": [],
            "errors": [{"step": "preflight_blocker", "error": b["title"]} for b in blockers],
        }

    # Resolve configured system_dir accurately (including 99_System!)
    cfg_sys = "System"
    try:
        snap = load_config(vault_root)
        cfg_sys = str(snap.values["system_dir"].value or "System")
    except Exception:  # noqa: BLE001
        if (vault_root / "paperforge.json").is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                raw_c = json.loads((vault_root / "paperforge.json").read_text(encoding="utf-8"))
                vc = raw_c.get("vault_config") if isinstance(raw_c.get("vault_config"), dict) else {}
                cfg_sys = str(vc.get("system_dir") or raw_c.get("system_dir") or "System")

    legacy_pf = _detect_legacy_engine_root(vault_root, cfg_sys)
    engine_root = (
        vault_root / ".paperforge"
        if (vault_root / ".paperforge" / "indexes").exists()
        else legacy_pf or (vault_root / ".paperforge")
    )

    ok_space, free_bytes = _check_disk_headroom(vault_root, 32 * 1024 * 1024)
    if not ok_space:
        return {
            "dry_run": False,
            "applied": False,
            "status": "failed",
            "plan": plan,
            "executed_steps": [],
            "errors": [{"step": "disk_space", "error": f"Insufficient disk space ({free_bytes} bytes free)"}],
        }

    backup_dir = _snapshot_preflight_backups(vault_root, engine_root, cfg_sys)
    executed_steps: list[dict[str, Any]] = [{"step": "preflight_backup", "backup_dir": str(backup_dir)}]
    errors: list[dict[str, str]] = []

    # 1. Config schema v2 migration
    if validate_config(vault_root).state == "migration_required":
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
                # O(1) directory rename/merge without blocking on 1,000+ workspace file scans
                moved_pairs: list[tuple[Path, Path]] = []
                target_pf = vault_root / ".paperforge"
                conflict_dir = target_pf / "backups" / "storage-migration"
                t_counts = _move_tree_entries(
                    legacy_pf,
                    target_pf,
                    dry_run=False,
                    moved_pairs=moved_pairs,
                    conflict_backup_dir=conflict_dir,
                )
                if (vault_root / "paperforge.json").is_file():
                    set_config(vault_root, "system_dir", ".paperforge")
                write_json_atomic(
                    backup_dir / "moved-pairs.json",
                    [{"src": str(s), "dst": str(d)} for s, d in moved_pairs],
                )
                with contextlib.suppress(OSError):
                    if legacy_pf.exists() and not any(legacy_pf.iterdir()):
                        legacy_pf.rmdir()
                    if legacy_pf.parent.exists() and legacy_pf.parent != vault_root and not any(legacy_pf.parent.iterdir()):
                        legacy_pf.parent.rmdir()
                executed_steps.append({"step": "fast_storage_cutover", "result": t_counts})
            else:
                sres = migrate_vault_storage(vault_root, dry_run=False, isolate_paper_errors=True)
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

    # 3. Resolve post-cutover paths & upgrade ONLY PaperForge-owned Base views
    try:
        paths = paperforge_paths(vault_root)
    except Exception:  # noqa: BLE001
        paths = {
            "vault": vault_root,
            "literature": vault_root / "Resources" / "Literature",
            "bases": vault_root / "Bases",
            "paperforge": vault_root / ".paperforge",
            "exports": vault_root / ".paperforge" / "exports",
            "config": vault_root / ".paperforge" / "config" / "domain-collections.json",
            "ocr": vault_root / ".paperforge" / "ocr",
        }

    try:
        exports_dir = paths.get("exports") or (vault_root / ".paperforge" / "exports")
        domain_cfg = load_domain_config(paths) if exports_dir.is_dir() else {"schema_version": 1, "domains": []}
        # Also include any PaperForge-owned `.base` files already present in `Bases/`
        existing_domains = {d.get("domain") for d in domain_cfg.get("domains", [])}
        base_dir = paths.get("bases")
        if base_dir and base_dir.is_dir():
            for bf in sorted(base_dir.glob("*.base")):
                if bf.name == "Literature Hub.base":
                    continue
                txt = bf.read_text(encoding="utf-8", errors="ignore")
                if _is_paperforge_owned_base_file(txt, bf, set()) and bf.stem not in existing_domains:
                    domain_cfg.setdefault("domains", []).append(
                        {"domain": bf.stem, "export_file": f"{bf.stem}.json", "allowed_collections": []}
                    )
        if domain_cfg.get("domains") or (base_dir and (base_dir / "Literature Hub.base").exists()):
            ensure_base_views(vault_root, paths, domain_cfg)
        executed_steps.append({"step": "base_views_upgrade", "ok": True})
    except Exception as exc:  # noqa: BLE001
        errors.append({"step": "base_views_upgrade", "error": str(exc)})

    # 4. Progressive healing (immediate in full mode; deferred to background daemon in fast_cutover mode)
    if not fast_cutover and rebuild_db:
        try:
            heal_res = heal_vault_progressive(vault_root, backfill_ocr=backfill_ocr)
            executed_steps.append({"step": "progressive_heal", "result": heal_res})
            for si in heal_res.get("skipped_isolated") or []:
                errors.append(
                    {
                        "step": f"progressive_heal:{si.get('key', 'unknown')}",
                        "error": str(si.get("reason") or "workspace heal skipped"),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "progressive_heal", "error": str(exc)})
    elif not fast_cutover:
        try:
            heal_res = heal_vault_progressive(vault_root, limit=None, backfill_ocr=backfill_ocr)
            executed_steps.append({"step": "workspace_normalize", "result": heal_res})
            for si in heal_res.get("skipped_isolated") or []:
                errors.append(
                    {
                        "step": f"workspace_normalize:{si.get('key', 'unknown')}",
                        "error": str(si.get("reason") or "workspace normalize skipped"),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            errors.append({"step": "workspace_normalize", "error": str(exc)})

    # 5. Confirmed residual quarantine (supports selective `quarantine_ids`)
    selected_ids: set[str] | None = None
    if quarantine_ids is not None:
        selected_ids = set(quarantine_ids)
    elif quarantine_residuals:
        selected_ids = {str(c["id"]) for c in plan["cleanup_candidates"]}

    if selected_ids:
        quarantined_count = 0
        for cand in plan["cleanup_candidates"]:
            if cand["id"] not in selected_ids:
                continue
            target_p = Path(cand["path"])
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

    settlement_status = "partial_success" if errors else "completed"

    # 6. Stamp `.paperforge/vault-manifest.json` with rollback reference
    try:
        manifest_path = write_vault_manifest(
            vault_root,
            migration_entry={
                "timestamp": _utcnow_compact(),
                "mode": "fast_cutover" if fast_cutover else "full",
                "status": settlement_status,
                "backup_dir": str(backup_dir),
                "steps": [s["step"] for s in executed_steps],
                "error_count": len(errors),
            },
        )
        executed_steps.append({"step": "write_vault_manifest", "path": str(manifest_path)})
    except Exception as exc:  # noqa: BLE001
        errors.append({"step": "write_vault_manifest", "error": str(exc)})
        settlement_status = "partial_success"

    return {
        "dry_run": False,
        "applied": True,
        "status": settlement_status,
        "mode": "fast_cutover" if fast_cutover else "full",
        "backup_dir": str(backup_dir),
        "healing_pending": bool(fast_cutover),
        "executed_steps": executed_steps,
        "errors": errors,
        "post_check": inspect_vault_upgrade(vault_root),
    }


def rollback_vault_upgrade(vault: Path, *, backup_dir: Path | None = None) -> dict[str, Any]:
    """One-Click Time-Machine rollback restoring directory structure, `paperforge.json`, and `.base` files."""
    from paperforge.services.storage_migration import rollback_incomplete_migration
    from paperforge.services.vault_engine import vault_manifest_path

    vault_root = Path(vault).expanduser().resolve()
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

    # Reverse fast_cutover moved_pairs or storage_migration journal
    moved_pairs_file = target_snap / "moved-pairs.json"
    if moved_pairs_file.is_file():
        pairs = json.loads(moved_pairs_file.read_text(encoding="utf-8"))
        for item in reversed(pairs):
            src_p = Path(item["src"])
            dst_p = Path(item["dst"])
            if dst_p.exists() and not src_p.exists():
                src_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst_p), str(src_p))
                restored_moves += 1
    else:
        journal_file = vault_root / ".paperforge" / ".migration-journal.json"
        if journal_file.is_file():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                jdata = json.loads(journal_file.read_text(encoding="utf-8"))
                for item in reversed(jdata.get("moved_pairs") or []):
                    src_p = Path(item["src"])
                    dst_p = Path(item["dst"])
                    if dst_p.exists() and not src_p.exists():
                        src_p.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst_p), str(src_p))
                        restored_moves += 1

    # Restore snapshotted configs and `.base` files
    for rel in ("paperforge.json", ".obsidian/plugins/paperforge/data.json"):
        snap_f = target_snap / rel
        if snap_f.is_file():
            dst_f = vault_root / rel
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(snap_f), str(dst_f))
            restored_files += 1

    for base_sub in ("Bases", "05_Bases"):
        s_bdir = target_snap / base_sub
        if s_bdir.is_dir():
            for bf in s_bdir.glob("*.base"):
                dst_bf = vault_root / base_sub / bf.name
                dst_bf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(bf), str(dst_bf))
                restored_files += 1

    mf = vault_manifest_path(vault_root)
    if mf.is_file():
        archived = target_snap / "rolled-back-vault-manifest.json"
        shutil.move(str(mf), str(archived))

    return {
        "rolled_back": True,
        "backup_dir": str(target_snap),
        "restored_moves": restored_moves,
        "restored_files": restored_files,
    }
