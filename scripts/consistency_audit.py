#!/usr/bin/env python3
"""PaperForge consistency audit script.

Checks hard constraints across the codebase:
1. No old command names in active code/docs
2. No paperforge_lite references in Python code
3. No dead internal links in markdown
4. All command/*.md files have valid structure

Exit code: 0 if all pass, 1 if any fail.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable

# Root of the repository (parent of this script)
REPO_ROOT = Path(__file__).parent.parent.resolve()

# Patterns for old command names that should NOT appear outside migration/historical docs
OLD_COMMAND_PATTERNS = {
    "paperforge selection-sync": r"paperforge\s+selection-sync",
    "paperforge index-refresh": r"paperforge\s+index-refresh",
    "paperforge ocr run": r"paperforge\s+ocr\s+run",
    "paperforge ocr doctor": r"paperforge\s+ocr\s+doctor",
    "/LD-deep": r"/LD-deep",
    "/LD-paper": r"/LD-paper",
    "/lp-ocr": r"/lp-ocr(?!\w)",  # word boundary
    "/lp-index-refresh": r"/lp-index-refresh",
    "/lp-selection-sync": r"/lp-selection-sync",
    "/lp-status": r"/lp-status(?!\w)",  # word boundary
}

# Files/directories to exclude from Check 1
CHECK1_EXCLUDES = {
    "docs/MIGRATION-v1.2.md",
    "docs/ARCHITECTURE.md",  # ADR-010 documents historical command names
    ".planning",
    ".pytest_cache",
    "__pycache__",
    ".git",
    "scripts/consistency_audit.py",  # Don't flag the audit script itself
}

# In Python code, these contexts are acceptable (backward compat aliases, tests, etc.)
CHECK1_PY_EXCLUDE_PATTERNS = [
    # Docstrings mentioning backward compatibility
    r"backward compat",
    r"deprecated",
    r"alias",
    r"命令迁移",  # migration note in Chinese
    r"migration",
    # Test files checking for old commands
    r"test_command_docs",
    r"test_.*dispatch",
    # Comments describing what a function handles
    r"Handle `paperforge ocr doctor`",
]

# Required sections in command/*.md files
COMMAND_DOC_REQUIRED_SECTIONS = [
    "Purpose",
    "CLI Equivalent",
    "Prerequisites",
    "Arguments",
    "Example",
    "Output",
    "Error Handling",
    "Platform Notes",
]


def should_exclude_check1(path: Path) -> bool:
    """Check if a path should be excluded from Check 1."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    for exclude in CHECK1_EXCLUDES:
        if rel.startswith(exclude) or exclude in rel:
            return True
    return False


def find_files(pattern: str, root: Path = REPO_ROOT) -> Iterable[Path]:
    """Find files matching a glob pattern, excluding common ignored dirs."""
    ignore_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
    for path in root.rglob(pattern):
        if any(part in ignore_dirs for part in path.parts):
            continue
        yield path


def check_old_commands() -> tuple[int, list[str]]:
    """Check 1: No old command names in active code/docs."""
    violations: list[str] = []

    # Check markdown files
    for md_path in find_files("*.md"):
        if should_exclude_check1(md_path):
            continue
        content = md_path.read_text(encoding="utf-8")
        rel = md_path.relative_to(REPO_ROOT).as_posix()
        for name, pattern in OLD_COMMAND_PATTERNS.items():
            for match in re.finditer(pattern, content):
                # Skip matches inside inline code that explicitly mention migration
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end]
                # Allow old commands in explicit migration sections of AGENTS.md
                if rel == "AGENTS.md" and "命令迁移说明" in content[:match.start()]:
                    # Check if this is in section 11 (migration section)
                    section_start = content.find("## 11. 命令迁移说明")
                    if section_start != -1 and match.start() > section_start:
                        continue
                violations.append(f"  [{rel}] {name}: {line.strip()}")

    # Check Python files (user-facing strings only)
    for py_path in find_files("*.py"):
        if should_exclude_check1(py_path):
            continue
        content = py_path.read_text(encoding="utf-8")
        rel = py_path.relative_to(REPO_ROOT).as_posix()
        for name, pattern in OLD_COMMAND_PATTERNS.items():
            for match in re.finditer(pattern, content):
                # Skip if in a test file or backward-compat code
                if "test_" in rel or "tests/" in rel:
                    continue
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                if line_end == -1:
                    line_end = len(content)
                line = content[line_start:line_end]
                # Skip docstrings/comments about backward compatibility
                stripped = line.strip()
                if any(re.search(p, stripped, re.IGNORECASE) for p in CHECK1_PY_EXCLUDE_PATTERNS):
                    continue
                # Skip CLI parser setup for backward compat aliases
                if "add_parser" in stripped or "help=" in stripped:
                    continue
                violations.append(f"  [{rel}] {name}: {stripped}")

    passed = len(violations) == 0
    return (0 if passed else 1), violations


def check_paperforge_lite() -> tuple[int, list[str]]:
    """Check 2: No paperforge_lite references in Python code."""
    violations: list[str] = []
    pattern = re.compile(r"paperforge_lite")

    for py_path in find_files("*.py"):
        rel = py_path.relative_to(REPO_ROOT).as_posix()
        # Skip the audit script itself
        if rel == "scripts/consistency_audit.py":
            continue
        content = py_path.read_text(encoding="utf-8")
        for match in pattern.finditer(content):
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_end = content.find("\n", match.end())
            if line_end == -1:
                line_end = len(content)
            line = content[line_start:line_end].strip()
            violations.append(f"  [{rel}] {line}")

    passed = len(violations) == 0
    return (0 if passed else 1), violations


def check_dead_links() -> tuple[int, list[str]]:
    """Check 3: No dead internal links in markdown."""
    violations: list[str] = []
    # Match markdown links: [text](path) or [text](./path)
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_path in find_files("*.md"):
        content = md_path.read_text(encoding="utf-8")
        rel = md_path.relative_to(REPO_ROOT).as_posix()
        for match in link_pattern.finditer(content):
            link_text = match.group(1)
            link_target = match.group(2)

            # Skip external URLs
            if link_target.startswith("http://") or link_target.startswith("https://"):
                continue
            # Skip anchor-only links
            if link_target.startswith("#"):
                continue
            # Skip mailto links
            if link_target.startswith("mailto:"):
                continue

            # Resolve the target relative to the current markdown file
            if link_target.startswith("/"):
                target_path = REPO_ROOT / link_target.lstrip("/")
            else:
                target_path = md_path.parent / link_target

            # Check if the target exists (file or directory)
            if not target_path.exists():
                # Try appending .md for implicit markdown links
                if not (target_path.with_suffix(".md")).exists():
                    violations.append(
                        f"  [{rel}] Dead link to '{link_target}' (text: '{link_text}')"
                    )

    passed = len(violations) == 0
    return (0 if passed else 1), violations


def check_command_docs() -> tuple[int, list[str]]:
    """Check 4: All command/*.md files have valid structure."""
    violations: list[str] = []
    command_dir = REPO_ROOT / "command"

    if not command_dir.exists():
        violations.append("  command/ directory not found")
        return 1, violations

    command_files = sorted(command_dir.glob("pf-*.md"))
    if not command_files:
        violations.append("  No command/pf-*.md files found")
        return 1, violations

    for cmd_path in command_files:
        content = cmd_path.read_text(encoding="utf-8")
        rel = cmd_path.relative_to(REPO_ROOT).as_posix()
        missing = []
        for section in COMMAND_DOC_REQUIRED_SECTIONS:
            # Look for ## Section or ## Section (subheading)
            if not re.search(rf"^##\s+{re.escape(section)}(\s|$)", content, re.MULTILINE):
                missing.append(section)
        if missing:
            violations.append(f"  [{rel}] Missing sections: {', '.join(missing)}")

    passed = len(violations) == 0
    return (0 if passed else 1), violations


def main() -> int:
    print("=== Consistency Audit Results ===\n")

    checks = [
        ("Check 1: No old command names", check_old_commands),
        ("Check 2: No paperforge_lite in Python", check_paperforge_lite),
        ("Check 3: No dead links", check_dead_links),
        ("Check 4: Command docs structure", check_command_docs),
    ]

    total_passed = 0
    total_failed = 0

    for name, check_fn in checks:
        exit_code, details = check_fn()
        status = "PASS" if exit_code == 0 else "FAIL"
        print(f"[{status}] {name}")
        if details:
            print(f"  Found: {len(details)} occurrence(s)")
            for detail in details:
                print(detail)
        else:
            print("  Found: 0 occurrences")
        print()

        if exit_code == 0:
            total_passed += 1
        else:
            total_failed += 1

    print("=== Summary ===")
    print(f"Passed: {total_passed}/{len(checks)}")
    print(f"Failed: {total_failed}/{len(checks)}")

    return 1 if total_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
