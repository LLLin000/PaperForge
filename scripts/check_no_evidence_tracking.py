#!/usr/bin/env python3
"""Refuse to track the research evidence corpus (``docs/evidence/``).

The corpus was published by accident once: 1,143 extracted paper images, paper
titles and local machine paths, in commit history as well as in the tree. A
``.gitignore`` entry alone does not stop ``git add -f``, so this is the gate.

Two scopes:
  * the current index (``git ls-files``) — the tree a clone would receive;
  * with ``--base REV``, files **added** between that revision and HEAD, which
    catches a corpus commit that was later deleted in the same branch.

Exit code: 0 clean, 1 offenders, 2 usage/git failure.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PURGE_PATH = "docs/evidence/"


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def tracked(repo: Path) -> list[str]:
    return [p for p in _git(repo, "ls-files", "--", "docs/evidence").splitlines() if p.strip()]


def added_since(repo: Path, base: str) -> list[str]:
    """Files the commits in ``base..HEAD`` ever added under the corpus path.

    A range diff would miss an add-then-delete: the endpoints agree, the branch
    does not. Walking the commits is the only honest measurement.
    """
    out = _git(
        repo,
        "log",
        "--format=",
        "--name-only",
        "--diff-filter=A",
        f"{base}..HEAD",
        "--",
        "docs/evidence",
    )
    return sorted({p.strip() for p in out.splitlines() if p.strip().startswith(PURGE_PATH)})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "gate").splitlines()[0])
    parser.add_argument("--repo", default=str(REPO_ROOT), help="repository to inspect")
    parser.add_argument("--base", help="also reject corpus files added since this revision")
    args = parser.parse_args(argv)

    repo = Path(args.repo)
    offenders = sorted({*tracked(repo), *(added_since(repo, args.base) if args.base else [])})
    if offenders:
        print("::error::the research evidence corpus must not be tracked", file=sys.stderr)
        for path in offenders[:50]:
            print(f"  {path}", file=sys.stderr)
        if len(offenders) > 50:
            print(f"  ... and {len(offenders) - 50} more", file=sys.stderr)
        return 1
    scope = f"index and additions since {args.base}" if args.base else "index"
    print(f"no evidence corpus in the {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
