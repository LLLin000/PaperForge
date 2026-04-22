#!/usr/bin/env python3
"""
PaperForge Lite 更新器

一键更新（推荐）:
    python update.py

高级用法:
    python update.py --check        # 仅检查，不安装
    python update.py --dry-run      # 预览更新内容
    python update.py --force        # 强制更新，不提示确认

安全保证：
    - 只更新代码文件，绝不触碰用户数据
    - 更新前自动备份
    - 失败自动回滚
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError

# =============================================================================
# 配置
# =============================================================================

GITHUB_REPO = "LLLin000/PaperForge"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"
GITHUB_ZIP = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/master.zip"

# Windows 编码修复
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 用户数据保护清单（绝不动这些路径）
PROTECTED_PATHS = {
    "03_Resources", "05_Bases",
    "99_System/PaperForge/ocr",
    "99_System/PaperForge/exports",
    "99_System/PaperForge/indexes",
    "99_System/PaperForge/candidates",
    ".env", "AGENTS.md",
}

# 可更新路径（代码文件）
UPDATEABLE_PATHS = ["skills", "pipeline", "command", "scripts"]


# =============================================================================
# 工具函数
# =============================================================================

def color(text: str, c: str = "") -> str:
    colors = {
        "r": "\033[91m", "g": "\033[92m", "y": "\033[93m",
        "b": "\033[94m", "c": "\033[96m", "x": "\033[0m",
    }
    if sys.platform == "win32" and not os.environ.get("FORCE_COLOR"):
        return text
    return f"{colors.get(c, '')}{text}{colors['x']}"


def log(msg: str, c: str = "") -> None:
    print(color(msg, c))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def is_git(path: Path) -> bool:
    return (path / ".git").is_dir()


def git(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")


# =============================================================================
# 版本检测
# =============================================================================

def local_version(vault: Path) -> str:
    return load_json(vault / "paperforge.json").get("version", "unknown")


def remote_version() -> str | None:
    """从 GitHub 获取远程版本"""
    try:
        req = Request(
            f"{GITHUB_API}/contents/paperforge.json",
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PaperForge"},
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            req2 = Request(data["download_url"], headers={"User-Agent": "PaperForge"})
            with urlopen(req2, timeout=10) as resp2:
                return json.loads(resp2.read()).get("version")
    except Exception:
        return None


def parse_v(v: str) -> tuple:
    return tuple(int(x) for x in v.split(".") if x.isdigit())


def newer(a: str, b: str) -> bool:
    try:
        return parse_v(a) > parse_v(b)
    except ValueError:
        return a != b


# =============================================================================
# 核心更新逻辑
# =============================================================================

def scan_updates(vault: Path, source: Path) -> list[tuple[Path, Path, str]]:
    """扫描需要更新的文件，返回 (src, dst, action) 列表"""
    updates = []
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
            if any(rel_str.startswith(p) for p in PROTECTED_PATHS):
                continue
            if dst.exists():
                if sha256(src) != sha256(dst):
                    updates.append((src, dst, "UPDATE"))
            else:
                updates.append((src, dst, "NEW"))
    return updates


def do_backup(vault: Path, updates: list) -> Path | None:
    """备份将被覆盖的文件"""
    backup_dir = vault / f".backup_{datetime.now():%Y%m%d_%H%M%S}"
    backup_dir.mkdir(exist_ok=True)
    count = 0
    for src, dst, action in updates:
        if action == "UPDATE" and dst.exists():
            bp = backup_dir / dst.relative_to(vault)
            bp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, bp)
            count += 1
    if count:
        log(f"[INFO] 已备份 {count} 个文件到 {backup_dir.name}", "c")
    return backup_dir if count else None


def do_update(vault: Path, updates: list) -> bool:
    """执行文件更新"""
    try:
        for src, dst, action in updates:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return True
    except Exception as e:
        log(f"[ERR] 更新失败: {e}", "r")
        return False


def do_rollback(vault: Path, backup_dir: Path) -> None:
    """从备份恢复"""
    log("[INFO] 正在回滚...", "b")
    for bp in backup_dir.rglob("*"):
        if bp.is_file():
            orig = vault / bp.relative_to(backup_dir)
            orig.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bp, orig)
    log("[OK] 回滚完成", "g")


# =============================================================================
# 更新模式：Git Pull
# =============================================================================

def update_git(vault: Path, dry: bool = False) -> bool:
    if not is_git(vault):
        log("[ERR] 不是 git 仓库", "r")
        return False
    status = git(["status", "--short"], vault)
    if status.stdout.strip():
        log("[WARN] 有未提交的更改，请先提交或储藏", "y")
        return False
    if dry:
        log("[WOULD] git pull origin master", "y")
        return True
    log("[INFO] 执行 git pull...", "b")
    r = git(["pull", "origin", "master"], vault)
    if r.returncode != 0:
        log(f"[ERR] git pull 失败: {r.stderr}", "r")
        return False
    log("[OK] git pull 成功", "g")
    if r.stdout.strip():
        print(r.stdout)
    return True


# =============================================================================
# 更新模式：Zip 下载
# =============================================================================

def update_zip(vault: Path, dry: bool = False) -> bool:
    log("[INFO] 下载更新包...", "b")
    tmp = Path(tempfile.mkdtemp(prefix="pf_update_"))
    zip_path = tmp / "update.zip"
    try:
        if not dry:
            req = Request(GITHUB_ZIP, headers={"User-Agent": "PaperForge"})
            with urlopen(req, timeout=60) as resp:
                zip_path.write_bytes(resp.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp / "extracted")
            dirs = [d for d in (tmp / "extracted").iterdir() if d.is_dir()]
            source = dirs[0] if dirs else None
        else:
            source = tmp / "PaperForge-master"
        if not source or not source.exists():
            log("[ERR] 解压失败", "r")
            return False
        return apply_updates(vault, source, dry)
    except Exception as e:
        log(f"[ERR] 下载失败: {e}", "r")
        return False
    finally:
        if not dry:
            shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# 通用更新应用
# =============================================================================

def apply_updates(vault: Path, source: Path, dry: bool = False) -> bool:
    updates = scan_updates(vault, source)
    if not updates:
        log("[OK] 所有文件已是最新", "g")
        return True
    log(f"\n[INFO] 发现 {len(updates)} 个文件需要更新:", "b")
    for src, dst, action in updates:
        log(f"  [{action}] {dst.relative_to(vault)}", "g" if action == "NEW" else "y")
    if dry:
        log("\n[INFO] 预览完成，未实际写入", "c")
        return True
    backup = do_backup(vault, updates)
    if do_update(vault, updates):
        log(f"\n[OK] 更新完成！共 {len(updates)} 个文件", "g")
        return True
    if backup:
        do_rollback(vault, backup)
    return False


# =============================================================================
# 主流程
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="PaperForge Lite 更新器")
    parser.add_argument("--check", action="store_true", help="仅检查版本，不更新")
    parser.add_argument("--dry-run", action="store_true", help="预览更新内容")
    parser.add_argument("--force", action="store_true", help="强制更新，不提示")
    parser.add_argument("--vault", default=".", help="Vault 路径")
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    if not (vault / "paperforge.json").exists():
        log(f"[ERR] 未找到 paperforge.json: {vault}", "r")
        return 1

    local = local_version(vault)
    remote = remote_version()

    if args.check:
        log(f"本地版本: {local}", "c")
        log(f"远程版本: {remote or 'unknown'}", "c")
        if remote and newer(remote, local):
            log(f"[INFO] 有新版本可用: {remote}", "y")
        else:
            log("[OK] 已是最新", "g")
        return 0

    # 默认行为：检查 + 更新
    log("=" * 50, "b")
    log("PaperForge Lite 更新", "b")
    log("=" * 50, "b")
    log(f"本地版本: {local}", "c")
    log(f"远程版本: {remote or 'unknown'}", "c")

    if not remote or not newer(remote, local):
        log("[OK] 当前已是最新版本", "g")
        return 0

    log(f"\n[INFO] 发现新版本: {local} -> {remote}", "y")

    if not args.force and not args.dry_run:
        log("[WARN] 更新前建议备份 Vault", "y")
        ans = input(color("确认更新? [y/N]: ", "y")).strip().lower()
        if ans not in ("y", "yes"):
            log("[INFO] 已取消", "c")
            return 0

    # 选择更新方式
    if is_git(vault):
        success = update_git(vault, args.dry_run)
    else:
        success = update_zip(vault, args.dry_run)

    if success and not args.dry_run:
        log("\n[OK] 更新完成！请重启 Obsidian", "g")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
