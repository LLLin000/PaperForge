#!/usr/bin/env python
"""Bump version across all PaperForge files and optionally create a release.

Usage:
    python scripts/bump.py 1.4.12              # specific version, commit + tag only
    python scripts/bump.py patch               # bump patch, commit + tag
    python scripts/bump.py patch --release     # bump, commit, tag, push, create GitHub release
    python scripts/bump.py minor --release -m "New feature X"   # release with custom notes
    python scripts/bump.py 2.0.0 --dry-run     # preview only
    python scripts/bump.py patch --no-git      # skip git entirely
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Both root_manifest and plugin_manifest are updated from the canonical __init__.py version —
# never edit version directly in manifest.json. The source of truth is __version__ in __init__.py.
FILES_TO_UPDATE = {
    "__init__": ROOT / "paperforge" / "__init__.py",
    "plugin_manifest": ROOT / "paperforge" / "plugin" / "manifest.json",
    "root_manifest": ROOT / "manifest.json",
}

PLUGIN_FILES = [
    ROOT / "paperforge" / "plugin" / "main.js",
    ROOT / "paperforge" / "plugin" / "styles.css",
    ROOT / "paperforge" / "plugin" / "manifest.json",
]


def read_current_version() -> str:
    content = FILES_TO_UPDATE["__init__"].read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not m:
        sys.exit("Cannot find __version__ in __init__.py")
    return m.group(1)


def bump_part(version: str, part: str) -> str:
    parts = [int(x) for x in version.split(".")]
    if part == "major":
        return f"{parts[0] + 1}.0.0"
    elif part == "minor":
        return f"{parts[0]}.{parts[1] + 1}.0"
    else:
        return f"{parts[0]}.{parts[1]}.{parts[2] + 1}"


def update_file(path: Path, old_ver: str, new_ver: str, dry: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    if old_ver not in content:
        print(f"  SKIP {path.name}: version {old_ver} not found")
        return False
    if dry:
        print(f"  WOULD update {path.name}: {old_ver} → {new_ver}")
        return True
    new_content = content.replace(old_ver, new_ver)
    path.write_text(new_content, encoding="utf-8")
    print(f"  {path.name}: {old_ver} → {new_ver}")
    return True


def run(cmd, **kwargs):
    subprocess.run(cmd, cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description="Bump PaperForge version")
    parser.add_argument("version", help="New version or bump part (major/minor/patch)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--no-git", action="store_true", help="Skip git commit/tag")
    parser.add_argument("--release", action="store_true", help="Push and create GitHub release")
    parser.add_argument("-m", "--message", default="", help="Release notes (one-line summary)")
    args = parser.parse_args()

    old_ver = read_current_version()
    new_ver = args.version if "." in args.version else bump_part(old_ver, args.version)

    print(f"Bump: {old_ver} → {new_ver}")

    for key, path in FILES_TO_UPDATE.items():
        update_file(path, old_ver, new_ver, args.dry_run)

    if args.dry_run:
        print("\nDry run — no changes made.")
        return

    if args.no_git:
        print("\nSkipping git — files updated on disk only.")
        return

    # Git add + commit + tag
    staged = [str(FILES_TO_UPDATE[k]) for k in FILES_TO_UPDATE]
    run(["git", "add"] + staged)
    run(["git", "commit", "-m", f"bump: {old_ver} -> {new_ver}"])

    # Verify the commit actually has the new version
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:paperforge/__init__.py"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        if new_ver not in result.stdout:
            sys.exit(f"VERIFY FAILED: __init__.py in HEAD does not contain version {new_ver}")
    except subprocess.CalledProcessError:
        sys.exit("VERIFY FAILED: cannot read __init__.py from HEAD")

    run(["git", "tag", "-f", new_ver])
    print(f"Committed and tagged {new_ver}")

    if not args.release:
        print("Run: git push && git push --tags")
        return

    # Push (may fail on protected branches — push to a release branch instead)
    try:
        run(["git", "push"])
    except subprocess.CalledProcessError:
        print("WARNING: git push failed (branch may be protected). Push manually or use a release branch.")
    try:
        run(["git", "push", "--tags"])
    except subprocess.CalledProcessError:
        print("WARNING: git push --tags failed")

    # Create GitHub release
    notes = args.message or f"v{new_ver}"
    release_args = [
        "gh", "release", "create", new_ver,
        "--title", new_ver,
        "--notes", notes,
    ]
    for pf in PLUGIN_FILES:
        release_args.append(str(pf))
    run(release_args)
    print(f"GitHub release v{new_ver} created with plugin assets")


if __name__ == "__main__":
    main()
