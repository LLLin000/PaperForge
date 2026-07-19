#!/usr/bin/env python3
"""Version consistency gate script.

Checks that all version declarations across the codebase match
the canonical version in paperforge.__version__.

Declaration locations checked:
1. paperforge/__init__.py (source of truth)
2. paperforge/plugin/manifest.json
3. paperforge/plugin/versions.json
4. pyproject.toml (dynamic version config)
5. paperforge/plugin/main.js (version fallback strings)

Exit code: 0 if all match, 1 if any mismatch.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_canonical_version() -> str:
    """Read version from paperforge.__init__."""
    init_path = REPO_ROOT / "paperforge" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not m:
        print("[FAIL] Cannot parse __version__ from paperforge/__init__.py")
        sys.exit(1)
    return m.group(1)


def check_init(canonical: str) -> list[str]:
    errors = []
    init_path = REPO_ROOT / "paperforge" / "__init__.py"
    content = init_path.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if m and m.group(1) != canonical:
        errors.append(f'  paperforge/__init__.py: __version__ = "{m.group(1)}" (expected "{canonical}")')
    return errors


def check_plugin_manifest(canonical: str) -> list[str]:
    errors = []
    path = REPO_ROOT / "paperforge" / "plugin" / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ver = data.get("version")
        if ver != canonical:
            errors.append(f'  paperforge/plugin/manifest.json: version = "{ver}" (expected "{canonical}")')
    except (json.JSONDecodeError, FileNotFoundError) as e:
        errors.append(f"  paperforge/plugin/manifest.json: failed to read — {e}")
    return errors


def check_root_manifest(canonical: str) -> list[str]:
    errors = []
    path = REPO_ROOT / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ver = data.get("version")
        if ver != canonical:
            errors.append(f'  manifest.json: version = "{ver}" (expected "{canonical}")')
    except (json.JSONDecodeError, FileNotFoundError) as e:
        errors.append(f"  manifest.json: failed to read — {e}")
    return errors


def check_versions_json(canonical: str) -> list[str]:
    errors = []
    path = REPO_ROOT / "paperforge" / "plugin" / "versions.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if canonical not in data:
            errors.append(f'  paperforge/plugin/versions.json: missing entry for version "{canonical}"')
    except (json.JSONDecodeError, FileNotFoundError) as e:
        errors.append(f"  paperforge/plugin/versions.json: failed to read — {e}")
    return errors


def check_pyproject_toml() -> list[str]:
    errors = []
    path = REPO_ROOT / "pyproject.toml"
    if not path.exists():
        errors.append("  pyproject.toml: not found")
        return errors
    content = path.read_text(encoding="utf-8")
    if 'dynamic = ["version"]' not in content:
        errors.append('  pyproject.toml: missing dynamic = ["version"]')
    if 'version = {attr = "paperforge.__version__"}' not in content:
        errors.append("  pyproject.toml: missing version attr reference")
    return errors


def check_main_js(canonical: str) -> list[str]:
    errors = []
    path = REPO_ROOT / "paperforge" / "plugin" / "main.js"
    if not path.exists():
        errors.append("  paperforge/plugin/main.js: not found")
        return errors
    content = path.read_text(encoding="utf-8")
    # Find hardcoded version strings in fallback patterns
    fallback_pattern = re.compile(r"['\"](\d+\.\d+\.\d+\w*)['\"]")
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        # Skip comments and non-fallback lines
        if "manifest.version" not in stripped and "this.manifest" not in stripped:
            continue
        for m in fallback_pattern.finditer(stripped):
            found = m.group(1)
            if found == canonical:
                continue
            errors.append(
                f'  paperforge/plugin/main.js:{i}: hardcoded version "{found}"'
                f' (expected "{canonical}" or dynamic from manifest)'
            )
    return errors


def main() -> int:
    canonical = get_canonical_version()
    print(f"Canonical version: {canonical}")
    print()

    checks: list[tuple[str, list[str]]] = [
        ("paperforge/__init__.py", check_init(canonical)),
        ("paperforge/plugin/manifest.json", check_plugin_manifest(canonical)),
        ("manifest.json", check_root_manifest(canonical)),
        ("paperforge/plugin/versions.json", check_versions_json(canonical)),
        ("pyproject.toml (dynamic version config)", check_pyproject_toml()),
        ("paperforge/plugin/main.js (fallback strings)", check_main_js(canonical)),
    ]

    total_errors = 0
    for label, errors in checks:
        if not errors:
            print(f"[PASS] {label}")
        else:
            print(f"[FAIL] {label}")
            for e in errors:
                print(e)
            total_errors += len(errors)

    print()
    if total_errors == 0:
        print("All version declarations are consistent.")
        return 0
    else:
        print(f"Found {total_errors} version mismatch(es).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
