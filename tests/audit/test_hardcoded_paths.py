"""Audit: detect hardcoded path literals that should come from config.

Fails when any Python file in paperforge/ uses a string literal matching
known config-driven path patterns. This catches code that bypasses the
config system and hardcodes assumptions about directory layout.

Run: pytest tests/audit/test_hardcoded_paths.py -v
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = ["paperforge"]

# Directory-name string literals used in path concatenation.
# These should come from the config system, not be hardcoded.
HARDCODED_DIR_LITERALS: list[re.Pattern] = [
    re.compile(r'["\']System["\']\s*/\s*["\']PaperForge'),
    re.compile(r'["\']System["\']\s*/\s*["\']Zotero["\']'),
    re.compile(r'["\']Resources["\']\s*/\s*["\']Literature'),
    re.compile(r'["\']indexes["\']\s*/\s*["\']'),
]

# Absolute Windows paths (D:\...) are never acceptable in committed code.
ABS_WIN_PATH = re.compile(r'["\'][A-Za-z]:(?:/|\\\\)')

# Exempt files — these are either the config truth source or known safe locations.
EXEMPT_PREFIXES = (
    "paperforge/skills",          # skill scripts, documented template paths
    "paperforge/config.py",          # canonical default definitions
    "paperforge/worker/_utils.py",   # reverse path builder for export
    "paperforge/worker/prune.py",    # defensive cfg.get() fallback patterns
    "paperforge/worker/discussion.py",  # defensive try/except fallback
    "paperforge/embedding",          # defensive fallback patterns
    "paperforge/memory/runtime_health.py",  # defensive fallback patterns
)


def _is_exempt(file_path: Path, root: Path) -> bool:
    rel = _rel(file_path, root)
    if not rel:
        return False
    return any(rel.startswith(ex) for ex in EXEMPT_PREFIXES)


def _rel(file_path: Path, root: Path) -> str:
    try:
        return file_path.relative_to(root).as_posix()
    except ValueError:
        return ""


def _check_file(path: Path, root: Path) -> list[tuple[int, str, str]]:
    if _is_exempt(path, root):
        return []
    violations: list[tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return violations
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = ABS_WIN_PATH.search(stripped)
        if m:
            violations.append((lineno, "absolute windows path", stripped[:100]))
            continue
        for pattern in HARDCODED_DIR_LITERALS:
            m = pattern.search(stripped)
            if m:
                matched = m.group()[:60]
                violations.append((lineno, matched, stripped[:100]))
                break
    return violations


def test_no_hardcoded_paths():
    """Fail if any Python source hardcodes a config-driven path."""
    all_violations: list[tuple[Path, int, str, str]] = []
    for py_file in sorted(REPO_ROOT.glob("paperforge/**/*.py")):
        hits = _check_file(py_file, REPO_ROOT)
        for lineno, match, line in hits:
            all_violations.append((py_file, lineno, match, line))
    if not all_violations:
        return
    lines = [f"Found {len(all_violations)} hardcoded path(s):"]
    for f, lineno, match, line in all_violations:
        rel = _rel(f, REPO_ROOT)
        lines.append(f"  {rel}:{lineno}  matched {match!r}")
        lines.append(f"           {line}")
    msg = "\n".join(lines)
    print(msg, file=sys.stderr)
    raise AssertionError(msg)
