#!/usr/bin/env python3
"""Find machine-identifying absolute paths in tracked files (or any revision).

A published repository must not name the author's home directory, projects
drive, or temporary trial roots: those strings identify the machine, and in
this repo they also appeared next to real paper identities.

Markers are deliberately narrow — the ones that can only belong to one machine
(`<home>`, `<root>/`, `<home>`). Synthetic fixtures such as
`C:\\Users\\name\\Zotero` or `D:\\path\\to\\vault` are not matched, and generic
install paths (`<programs>/Obsidian`) are out of scope.

Usage:
    python scripts/check_machine_paths.py                  # working tree
    python scripts/check_machine_paths.py --rev HEAD       # a commit
    python scripts/check_machine_paths.py --rev origin/master --allow docs/evidence/
    python scripts/check_machine_paths.py --list-local     # group by directory

Exit code: 0 = clean (outside allowed prefixes), 1 = offenders found.
"""
from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Each pattern is a machine identity, not a style preference.
MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("windows-home", re.compile(r"[Cc]:[\\/]+Users[\\/]+Lin(?:[\\/]|$)")),
    ("projects-drive", re.compile(r"[Dd]:[\\/]+L[\\/]")),
    ("posix-home", re.compile(r"<home>(?:/|$)")),
)


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def _tracked_files(rev: str | None) -> list[str]:
    if rev is None:
        return [line for line in _git("ls-files").splitlines() if line]
    return [line for line in _git("ls-tree", "-r", "--name-only", rev).splitlines() if line]


def _file_text(rev: str | None, path: str) -> str | None:
    try:
        if rev is None:
            return (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")
        return _git("show", f"{rev}:{path}")
    except (SystemExit, OSError):
        return None


def scan(rev: str | None) -> dict[str, list[tuple[str, str]]]:
    """path -> [(marker, sample line)] for every offender."""
    hits: dict[str, list[tuple[str, str]]] = {}
    for path in _tracked_files(rev):
        text = _file_text(rev, path)
        if not text or "\x00" in text[:2000]:
            continue
        for marker, pattern in MARKERS:
            match = pattern.search(text)
            if not match:
                continue
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            sample = text[line_start : line_end if line_end != -1 else len(text)].strip()
            hits.setdefault(path, []).append((marker, sample[:120]))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "check machine paths").splitlines()[0])
    parser.add_argument("--rev", help="check a revision instead of the working tree")
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        help="path prefix to ignore because its removal is already scheduled",
    )
    parser.add_argument("--list-local", action="store_true", help="group offenders by directory")
    args = parser.parse_args(argv)

    hits = scan(args.rev)
    allowed, offenders = [], []
    for path, found in hits.items():
        if any(path.startswith(prefix) for prefix in args.allow):
            allowed.append(path)
        else:
            offenders.append((path, found))

    if args.list_local:
        buckets = collections.Counter(
            "/".join(path.split("/")[:2]) for path, _ in offenders
        )
        for bucket, count in buckets.most_common():
            print(f"{count:5d}  {bucket}/")
        print(f"{len(offenders):5d} files outside the allowlist, {len(allowed)} allowed")

    for path, found in sorted(offenders):
        marker = ", ".join({m for m, _ in found})
        print(f"{path}: {marker} :: {found[0][1]}")

    if offenders:
        print(
            f"\n{len(offenders)} tracked file(s) name this machine"
            + (f" ({len(allowed)} more under an allowed prefix)" if allowed else ""),
            file=sys.stderr,
        )
        return 1
    print("no machine-identifying paths" + (f" ({len(allowed)} under allowed prefixes)" if allowed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
