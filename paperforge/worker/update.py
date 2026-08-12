from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path

from paperforge.config import load_vault_config
from paperforge.worker.status import GITHUB_REPO, GITHUB_ZIP, UPDATEABLE_PATHS

logger = logging.getLogger(__name__)
GITHUB_PIP_SOURCE = f"git+https://github.com/{GITHUB_REPO}.git"


def _sync_obsidian_plugin(vault: Path) -> None:
    """Reload utils and sync the Obsidian plugin into the current vault."""
    import importlib

    import paperforge.worker._utils as _pf_utils

    importlib.reload(_pf_utils)
    _pf_utils.install_obsidian_plugin(vault)


def protected_paths(vault: Path) -> set[str]:
    cfg = load_vault_config(vault)
    pf = f"{cfg['system_dir']}/PaperForge"
    return {
        cfg["resources_dir"],
        cfg["base_dir"],
        f"{pf}/ocr",
        f"{pf}/exports",
        f"{pf}/indexes",
        f"{pf}/candidates",
        ".env",
        "AGENTS.md",
    }


def _remote_version() -> str | None:
    """Read version from __init__.py on GitHub (single source of truth)."""
    import re

    try:
        api = f"https://api.github.com/repos/{GITHUB_REPO}/contents/paperforge/__init__.py"
        req = urllib.request.Request(
            api, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PaperForge"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            content_b64 = data.get("content", "")
            if not content_b64:
                return None
            content = base64.b64decode(content_b64).decode("utf-8")
            m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
            return m.group(1) if m else None
    except Exception as e:
        logger.warning("Remote version check failed: %s", e)
        return None


def _scan_updates(vault: Path, source: Path) -> list[tuple[Path, Path, str]]:
    updates = []
    protected = protected_paths(vault)
    for name in UPDATEABLE_PATHS:
        src_dir = source / name
        if not src_dir.exists():
            continue
        for src in src_dir.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(source)
            dst = vault / rel
            rel_str = str(rel).replace("\\", "/")
            if any(rel_str.startswith(p) for p in protected):
                continue
            if dst.exists():
                if hashlib.sha256(src.read_bytes()).hexdigest() != hashlib.sha256(dst.read_bytes()).hexdigest():
                    updates.append((src, dst, "UPDATE"))
            else:
                updates.append((src, dst, "NEW"))
    return updates


def _do_backup(vault: Path, updates: list) -> Path | None:
    backup_dir = vault / f".backup_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(exist_ok=True)
    count = 0
    for _src, dst, action in updates:
        if action == "UPDATE" and dst.exists():
            bp = backup_dir / dst.relative_to(vault)
            bp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bp)
            count += 1
    if count:
        logger.info("已备份 %d 个文件到 %s", count, backup_dir.name)
    return backup_dir if count else None


def _apply_updates(vault: Path, updates: list) -> bool:
    try:
        for src, dst, _action in updates:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return True
    except Exception as e:
        logger.error("更新失败: %s", e)
        return False


def _rollback(vault: Path, backup_dir: Path) -> None:
    logger.info("正在回滚...")
    for bp in backup_dir.rglob("*"):
        if bp.is_file():
            orig = vault / bp.relative_to(backup_dir)
            orig.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bp, orig)
    logger.info("回滚完成")


def _detect_install_method() -> tuple[str, Path | None]:
    """Detect how paperforge is installed."""
    import paperforge

    pkg_dir = Path(paperforge.__file__).parent.resolve()

    # Check if installed in site-packages (pip install)
    if "site-packages" in str(pkg_dir) or "dist-packages" in str(pkg_dir):
        return ("pip", pkg_dir)

    # Check if in editable mode (pip install -e .)
    if pkg_dir.name == "paperforge" and (pkg_dir.parent / ".git").exists():
        return ("pip-editable", pkg_dir.parent)

    # Check if vault has .git (git clone)
    vault = Path.cwd()
    if (vault / ".git").exists():
        return ("git", vault)

    return ("unknown", None)


def _update_via_pip(editable: bool = False) -> bool:
    """Update via pip install."""
    cmd = [sys.executable, "-m", "pip", "install"]
    if editable:
        cmd.extend(["-e", "."])
    else:
        cmd.append("--upgrade")
        cmd.append("paperforge")

    logger.info("执行: %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        logger.warning("PyPI 更新失败，尝试 git: %s", r.stderr[:200])
        cmd[-1] = GITHUB_PIP_SOURCE
        logger.info("执行: %s", " ".join(cmd))
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            logger.error("pip 更新失败: %s", r.stderr)
            return False
    logger.info("pip 更新成功")
    return True


def _update_via_git(vault: Path) -> bool:
    """Update via git pull."""
    if not (vault / ".git").is_dir():
        logger.error("不是 git 仓库")
        return False
    r = subprocess.run(
        ["git", "status", "--short"], cwd=vault, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.stdout.strip():
        logger.warning("有未提交的更改，请先提交或储藏")
        return False
    logger.info("执行 git pull...")
    r = subprocess.run(
        ["git", "pull", "origin", "master"],
        cwd=vault,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        logger.error("git pull 失败: %s", r.stderr)
        return False
    logger.info("git pull 成功")
    return True


def update_via_zip(vault: Path) -> bool:
    logger.info("下载更新包...")
    tmp = Path(tempfile.mkdtemp(prefix="pf_update_"))
    zip_path = tmp / "update.zip"
    try:
        req = urllib.request.Request(GITHUB_ZIP, headers={"User-Agent": "PaperForge"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_path.write_bytes(resp.read())
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp / "extracted")
        dirs = [d for d in (tmp / "extracted").iterdir() if d.is_dir()]
        source = dirs[0] if dirs else None
        if not source:
            logger.error("解压失败")
            return False
        updates = _scan_updates(vault, source)
        if not updates:
            logger.info("所有文件已是最新")
            return True
        logger.info("发现 %d 个文件需要更新:", len(updates))
        for _src, dst, action in updates:
            logger.info("  [%s] %s", action, dst.relative_to(vault))
        backup = _do_backup(vault, updates)
        if _apply_updates(vault, updates):
            logger.info("更新完成！共 %d 个文件", len(updates))
            return True
        if backup:
            _rollback(vault, backup)
        return False
    except Exception as e:
        logger.error("下载失败: %s", e)
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _deploy_all_skills(vault: Path) -> None:
    """Deploy latest skills and AGENTS.md to vault after update."""
    try:
        from paperforge.config import load_vault_config
        from paperforge.services.skill_deploy import deploy_skills

        config = load_vault_config(vault)
        agent_key = config.get("agent_platform") or "opencode"
        result = deploy_skills(vault=vault, agent_key=agent_key, overwrite=True)
        if result["skill_deployed"]:
            logger.info("已部署 paperforge skill")
        if result["agents_md"]:
            logger.info("已更新 AGENTS.md")
        for err in result.get("errors", []):
            logger.warning("Skill 部署警告: %s", err)
    except Exception as e:
        logger.warning("Skill 部署失败（非致命）: %s", e)


def _fresh_installed_version() -> str | None:
    """Verify the ACTUALLY installed version with a fresh child interpreter
    (#174): the running process's paperforge module may be a stale import
    cache — never trust it for the post-update pointer."""
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import paperforge; print(paperforge.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        version = r.stdout.strip()
        return version if r.returncode == 0 and version else None
    except Exception:  # noqa: BLE001 — verification failure means no publish
        return None


def perform_update(vault: Path, *, ndjson: bool = False) -> dict:
    """Non-interactive lifecycle update (#174).

    Pure service contract: no prompts, no stdout printing, no UI
    confirmation (the #145 action runner / CLI UX owns confirmation).
    On a successful install the installed version is verified with a fresh
    child interpreter; ONLY then is the pointer published, with the
    OBSERVED version — publication is part of lifecycle success and must
    precede any success return.

    ndjson: emit the #137 stream (start / phase / exactly-one result|error
    terminal) with cooperative cancellation (stdin PAPERFORGE_STOP / SIGINT
    / SIGTERM → `cancelled` terminal, rc 130 at the CLI).
    """
    if ndjson:
        from paperforge.core.cancellation import make_cancellation_token
        from paperforge.core.ndjson import emit_phase, emit_start

        emit_start("foundation.update")
        _is_stopped, _restore = make_cancellation_token()
    else:
        _is_stopped, _restore = (lambda: False), (lambda: None)

    def _phase(label: str) -> bool:
        """Emit a phase; returns True when cancelled."""
        if ndjson:
            emit_phase("foundation.update", phase=label)
        return _is_stopped()
    def _finish(result: dict) -> dict:
        """Emit exactly-one #137 terminal; publication already happened
        before any success return, and cancellation returns rc 130 at the
        CLI."""
        if ndjson:
            from paperforge import __version__ as PF_VERSION
            from paperforge.core.errors import ErrorCode
            from paperforge.core.ndjson import emit_terminal
            from paperforge.core.result import PFError, PFResult

            event = "cancelled" if result.get("cancelled") else (
                "result" if result["ok"] else "error"
            )
            pf = PFResult(
                ok=result["ok"],
                command="update",
                version=PF_VERSION,
                data={k: v for k, v in result.items() if k not in ("ok", "cancelled")},
                error=(
                    PFError(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=result.get("error", "update failed"),
                    )
                    if event != "result"
                    else None
                ),
            )
            emit_terminal(event, "foundation.update", pf)
            _restore()
        return result

    try:
        import paperforge

        local = paperforge.__version__
    except Exception:
        local = "unknown"
    if _phase("check") or _is_stopped():
        return _finish({"ok": False, "updated": False, "local_version": local,
                "cancelled": True})
    remote = _remote_version()
    if not remote:
        return _finish({"ok": False, "updated": False, "local_version": local,
                "remote_version": None, "error": "cannot resolve remote version"})
    try:
        needs = tuple(int(x) for x in remote.split(".") if x.isdigit()) > tuple(
            int(x) for x in local.split(".") if x.isdigit()
        )
    except ValueError:
        needs = remote != local

    if not needs:
        _sync_obsidian_plugin(vault)
        _deploy_all_skills(vault)
        return _finish({"ok": True, "updated": False, "local_version": local,
                "remote_version": remote, "installed_version": local})

    # Auto-detect installation method
    if _phase("install") or _is_stopped():
        return _finish({"ok": False, "updated": False, "local_version": local,
                "cancelled": True})
    method, path = _detect_install_method()
    if method == "pip":
        success = _update_via_pip(editable=False)
        if not success:
            success = _update_via_zip(vault)
    elif method == "pip-editable":
        if path and (path / ".git").exists():
            success = _update_via_git(path)
            if success:
                os.chdir(path)
                success = _update_via_pip(editable=True)
            if not success:
                success = _update_via_zip(vault)
        else:
            success = _update_via_pip(editable=False)
            if not success:
                success = _update_via_zip(vault)
    elif method == "git":
        success = _update_via_git(vault)
        if not success:
            success = _update_via_zip(vault)
    else:
        success = _update_via_zip(vault)

    if not success:
        return _finish({"ok": False, "updated": False, "local_version": local,
                "remote_version": remote, "error": "install failed"})

    # Fresh-child verify BEFORE any success is returned.
    if _phase("verify") or _is_stopped():
        return _finish({"ok": False, "updated": False, "local_version": local,
                "cancelled": True})
    observed = _fresh_installed_version()
    if not observed or observed != remote:
        return _finish(
            {
                "ok": False,
                "updated": True,
                "local_version": local,
                "remote_version": remote,
                "installed_version": observed,
                "error": (
                    f"installed version {observed!r} != intended {remote!r}"
                ),
            }
        )

    _sync_obsidian_plugin(vault)
    _deploy_all_skills(vault)

    from paperforge.runtime_pointer import publish_pointer

    publish_pointer(paperforge_version=observed)
    return _finish({"ok": True, "updated": True, "local_version": local,
            "remote_version": remote, "installed_version": observed})


def run_update(vault: Path) -> int:
    """CLI UX over perform_update: adds the interactive confirmation prompt
    and human logging; no lifecycle logic lives here."""
    import paperforge

    try:
        local = paperforge.__version__
    except Exception:
        local = "unknown"
    remote = _remote_version()
    logger.info("%s", "=" * 50)
    logger.info("PaperForge 更新")
    logger.info("%s", "=" * 50)
    logger.info("本地版本: %s", local)
    logger.info("远程版本: %s", remote or "unknown")
    if not remote:
        logger.error("无法获取远程版本")
        return 1
    if not tuple(int(x) for x in remote.split(".") if x.isdigit()) > tuple(
        int(x) for x in local.split(".") if x.isdigit()
    ):
        _sync_obsidian_plugin(vault)
        _deploy_all_skills(vault)
        logger.info("当前已是最新版本")
        return 0
    logger.info("发现新版本: %s -> %s", local, remote)
    logger.warning("更新前建议备份 Vault")
    ans = input("确认更新? [y/N]: ").strip().lower()
    if ans not in ("y", "yes"):
        logger.info("已取消")
        return 0
    result = perform_update(vault)
    if result["ok"]:
        logger.info("更新完成！请重启 Obsidian")
        return 0
    logger.error("更新失败: %s", result.get("error"))
    return 1


# =============================================================================
# Main
# =============================================================================
