#!/usr/bin/env python3
"""Validate a PaperForge installation."""

from __future__ import annotations

import json
import os
from pathlib import Path


def check_path(label: str, path: Path, expected_type: str = "file") -> tuple[bool, str]:
    if not path.exists():
        return False, f"[FAIL] {label}: not found at {path}"
    if expected_type == "file" and not path.is_file():
        return False, f"[FAIL] {label}: exists but is not a file ({path})"
    if expected_type == "dir" and not path.is_dir():
        return False, f"[FAIL] {label}: exists but is not a directory ({path})"
    return True, f"[OK] {label}: {path}"


def load_config(vault: Path) -> dict:
    """Load vault configuration — prefers shared resolver, falls back to legacy."""
    # Try shared resolver first (01-03 and later installs)
    try:
        from paperforge.config import load_vault_config as _shared_load

        return _shared_load(vault)
    except ImportError:
        pass

    # Legacy fallback for pre-01-03 installs
    defaults = {
        "system_dir": "99_System",
        "resources_dir": "03_Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "05_Bases",
        "skill_dir": ".opencode/skills",
    }
    config_path = vault / "paperforge.json"
    if not config_path.exists():
        return defaults
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    nested = data.get("vault_config", {}) if isinstance(data.get("vault_config"), dict) else {}
    return {**defaults, **nested, **{k: v for k, v in data.items() if k in defaults and v}}


def resolve_vault_for_validate() -> Path:
    """Resolve vault path: PAPERFORGE_VAULT first, then VAULT_PATH, then cwd."""
    if "PAPERFORGE_VAULT" in os.environ and os.environ["PAPERFORGE_VAULT"]:
        return Path(os.environ["PAPERFORGE_VAULT"]).expanduser().resolve()
    if "VAULT_PATH" in os.environ and os.environ["VAULT_PATH"]:
        return Path(os.environ["VAULT_PATH"]).expanduser().resolve()
    return Path.cwd().resolve()


def validate_python_deps() -> list[tuple[bool, str]]:
    results = []
    required = {"requests": "requests", "pymupdf": "fitz", "pillow": "PIL", "textual": "textual"}
    for package, import_name in required.items():
        try:
            __import__(import_name)
            results.append((True, f"[OK] Python package installed: {package}"))
        except ImportError:
            results.append((False, f"[FAIL] Python package missing: {package}"))
    return results


def validate_vault(vault: Path, cfg: dict) -> list[tuple[bool, str]]:
    results = [check_path("Obsidian vault", vault, "dir")]
    if not results[0][0]:
        return results
    pf_root = vault / cfg["system_dir"] / "PaperForge"
    control_root = vault / cfg["resources_dir"] / cfg["control_dir"] / "library-records"
    literature_root = vault / cfg["resources_dir"] / cfg["literature_dir"]
    base_root = vault / cfg["base_dir"]
    for label, path, kind in [
        ("paperforge.json", vault / "paperforge.json", "file"),
        ("PaperForge root", pf_root, "dir"),
        ("exports directory", pf_root / "exports", "dir"),
        ("ocr directory", pf_root / "ocr", "dir"),
        ("domain config", pf_root / "config" / "domain-collections.json", "file"),
        ("worker script", pf_root / "worker" / "scripts" / "literature_pipeline.py", "file"),
        ("library records directory", control_root, "dir"),
        ("literature notes directory", literature_root, "dir"),
        ("Base directory", base_root, "dir"),
    ]:
        results.append(check_path(label, path, kind))
    env_path = pf_root / ".env"
    ok, msg = check_path("PaperForge .env", env_path, "file")
    results.append((ok, msg))
    if ok:
        env_text = env_path.read_text(encoding="utf-8")
        for key in ("PADDLEOCR_API_TOKEN", "PADDLEOCR_JOB_URL"):
            results.append((key in env_text, f"[{'OK' if key in env_text else 'FAIL'}] {key} configured"))
    return results


def validate_agent(vault: Path, cfg: dict) -> list[tuple[bool, str]]:
    skill_root = vault / cfg["skill_dir"] / "literature-qa"
    results = [
        check_path("LD-deep script", skill_root / "scripts" / "ld_deep.py", "file"),
        check_path("LD-deep subagent prompt", skill_root / "prompt_deep_subagent.md", "file"),
        check_path("chart-reading directory", skill_root / "chart-reading", "dir"),
    ]
    chart_dir = skill_root / "chart-reading"
    if chart_dir.exists():
        guide_count = len(list(chart_dir.glob("*.md")))
        results.append(
            (guide_count >= 14, f"[{'OK' if guide_count >= 14 else 'WARN'}] chart-reading guides: {guide_count}")
        )
    return results


def main() -> int:
    vault = resolve_vault_for_validate()
    cfg = load_config(vault)
    all_results = []
    all_results.extend(validate_python_deps())
    all_results.extend(validate_vault(vault, cfg))
    all_results.extend(validate_agent(vault, cfg))

    passed = sum(1 for ok, _ in all_results if ok)
    failed = [msg for ok, msg in all_results if not ok and not msg.startswith("[WARN]")]
    warnings = [msg for ok, msg in all_results if not ok and msg.startswith("[WARN]")]
    print(f"PaperForge validation: {passed} passed, {len(failed)} failed, {len(warnings)} warnings")
    for _, msg in all_results:
        print(msg)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
