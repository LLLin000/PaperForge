#!/usr/bin/env python3
"""Validate literature workflow setup."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def check_path(label: str, path: str | Path, expected_type: str = "file") -> tuple[bool, str]:
    """Check if a path exists and is the expected type."""
    p = Path(path)
    if not p.exists():
        return False, f"[FAIL] {label}: not found at {path}"
    
    if expected_type == "file" and not p.is_file():
        return False, f"[FAIL] {label}: exists but is not a file ({path})"
    if expected_type == "dir" and not p.is_dir():
        return False, f"[FAIL] {label}: exists but is not a directory ({path})"
    
    return True, f"[OK] {label}: {path}"


def validate_zotero(zotero_path: str) -> list[tuple[bool, str]]:
    """Validate Zotero installation and data directory."""
    results = []
    zotero_dir = Path(zotero_path)
    
    # Check main directory
    ok, msg = check_path("Zotero data directory", zotero_path, "dir")
    results.append((ok, msg))
    if not ok:
        return results
    
    # Check zotero.sqlite
    sqlite_path = zotero_dir / "zotero.sqlite"
    ok, msg = check_path("zotero.sqlite", sqlite_path, "file")
    results.append((ok, msg))
    
    # Check better-bibtex JSON (optional but recommended)
    bbt_path = zotero_dir / "better-bibtex.json"
    if bbt_path.exists():
        results.append((True, f"[OK] Better BibTeX config: {bbt_path}"))
    else:
        results.append((False, f"[WARN] Better BibTeX config not found (optional but recommended): {bbt_path}"))
    
    return results


def validate_obsidian(vault_path: str) -> list[tuple[bool, str]]:
    """Validate Obsidian vault structure."""
    results = []
    vault_dir = Path(vault_path)
    
    ok, msg = check_path("Obsidian vault", vault_path, "dir")
    results.append((ok, msg))
    if not ok:
        return results
    
    # Check expected subdirectories
    expected_dirs = [
        "00_Inbox",
        "01_Projects", 
        "02_Areas",
        "03_Resources",
        "04_Archives",
        "05_Bases",
        "99_System",
    ]
    
    for subdir in expected_dirs:
        subpath = vault_dir / subdir
        ok, msg = check_path(f"Vault subdirectory: {subdir}", subpath, "dir")
        results.append((ok, msg))
    
    return results


def validate_ocr_pipeline(vault_path: str) -> list[tuple[bool, str]]:
    """Validate OCR pipeline configuration."""
    results = []
    vault_dir = Path(vault_path)
    
    # Check .env file
    env_path = vault_dir / ".env"
    ok, msg = check_path("Environment config (.env)", env_path, "file")
    results.append((ok, msg))
    
    if ok:
        # Check if PADDLEOCR_API_KEY is set
        env_content = env_path.read_text(encoding="utf-8")
        if "PADDLEOCR_API_KEY" in env_content:
            results.append((True, "[OK] PADDLEOCR_API_KEY configured in .env"))
        else:
            results.append((False, "[FAIL] PADDLEOCR_API_KEY not found in .env"))
    
    # Check OCR pipeline directory
    ocr_dir = vault_dir / "99_System" / "LiteraturePipeline" / "worker"
    ok, msg = check_path("OCR pipeline directory", ocr_dir, "dir")
    results.append((ok, msg))
    
    # Check worker script
    worker_path = ocr_dir / "scripts" / "literature_pipeline.py"
    ok, msg = check_path("OCR worker script", worker_path, "file")
    results.append((ok, msg))
    
    return results


def validate_ld_deep(vault_path: str) -> list[tuple[bool, str]]:
    """Validate /LD-deep command setup."""
    results = []
    vault_dir = Path(vault_path)
    
    # Check ld_deep.py script
    ld_deep_path = vault_dir / ".opencode" / "skills" / "literature-qa" / "scripts" / "ld_deep.py"
    ok, msg = check_path("LD-deep script", ld_deep_path, "file")
    results.append((ok, msg))
    
    # Check prompt
    prompt_path = vault_dir / ".opencode" / "skills" / "literature-qa" / "prompt_deep_subagent.md"
    ok, msg = check_path("LD-deep subagent prompt", prompt_path, "file")
    results.append((ok, msg))
    
    # Check chart reading guides
    chart_guide_dir = vault_dir / "99_System" / "Template" / "读图指南"
    ok, msg = check_path("Chart reading guides directory", chart_guide_dir, "dir")
    results.append((ok, msg))
    
    if ok:
        # Count guide files
        guide_files = list(chart_guide_dir.glob("*.md"))
        if len(guide_files) >= 14:
            results.append((True, f"[OK] Found {len(guide_files)} chart reading guides"))
        else:
            results.append((False, f"[WARN] Only {len(guide_files)} chart guides found (expected 14+)"))
    
    return results


def validate_python_deps() -> list[tuple[bool, str]]:
    """Check Python dependencies."""
    results = []
    required = {
        "requests": "requests",
        "pymupdf": "fitz",
        "pillow": "PIL",
        "pytest": "pytest",
    }
    
    for package, import_name in required.items():
        try:
            __import__(import_name)
            results.append((True, f"[OK] Python package installed: {package}"))
        except ImportError:
            results.append((False, f"[FAIL] Python package missing: {package} (pip install {package})"))
    
    return results


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("Literature Workflow Setup Validation")
    print("=" * 60)
    
    # Load config from .env or config.json
    vault_path = os.environ.get("VAULT_PATH", ".")
    zotero_path = os.environ.get("ZOTERO_PATH", "")
    
    config_path = Path(vault_path) / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        vault_path = config.get("vault_path", vault_path)
        zotero_path = config.get("zotero_path", zotero_path)
    
    all_results = []
    
    # Python dependencies
    print("\n## Python Dependencies")
    all_results.extend(validate_python_deps())
    
    # Zotero
    if zotero_path:
        print("\n## Zotero Integration")
        all_results.extend(validate_zotero(zotero_path))
    else:
        all_results.append((False, "[SKIP] Zotero path not configured"))
    
    # Obsidian vault
    print("\n## Obsidian Vault")
    all_results.extend(validate_obsidian(vault_path))
    
    # OCR pipeline
    print("\n## OCR Pipeline")
    all_results.extend(validate_ocr_pipeline(vault_path))
    
    # LD-deep
    print("\n## LD-deep Commands")
    all_results.extend(validate_ld_deep(vault_path))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for ok, _ in all_results if ok)
    failed = sum(1 for ok, _ in all_results if not ok)
    warnings = sum(1 for ok, msg in all_results if not ok and msg.startswith("[WARN]"))
    
    print(f"Results: {passed} passed, {failed} failed ({warnings} warnings)")
    print("=" * 60)
    
    # Print failures
    failures = [msg for ok, msg in all_results if not ok and not msg.startswith("[WARN]")]
    if failures:
        print("\n### Failures to fix:")
        for msg in failures:
            print(f"  - {msg}")
    
    warnings_list = [msg for ok, msg in all_results if not ok and msg.startswith("[WARN]")]
    if warnings_list:
        print("\n### Warnings (optional):")
        for msg in warnings_list:
            print(f"  - {msg}")
    
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
