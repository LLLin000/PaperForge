#!/usr/bin/env python3
"""Audit which GitHub pull-request refs can still reach the evidence corpus.

Rewriting master and tags does not touch ``refs/pull/*``: GitHub owns those
refs and a closed or merged PR keeps its history fetchable. So the unit of
measurement is not "does the PR's current tree contain docs/evidence" but "can
any commit reachable from that ref reach an evidence blob".

Reports, per PR ref: reachable evidence blobs (history) versus evidence paths in
the ref's current tree, plus the PR state. Nothing is written to the repository.

Usage:
    python scripts/dev/pr_ref_reachability.py --fetch
    python scripts/dev/pr_ref_reachability.py --limit 20
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PURGE_PATH = "docs/evidence"
REF_PREFIX = "refs/pr-audit"


def git(*args: str) -> str:
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


def fetch_pr_refs() -> int:
    """Mirror refs/pull/*/head into a local namespace (read-only on GitHub)."""
    # An explicit refspec: never rewrite remote.origin.fetch, or every later
    # `git fetch` in this checkout would pull all 186 review refs.
    git("fetch", "--quiet", "--no-tags", "origin", "+refs/pull/*/head:refs/pr-audit/*")
    return len([line for line in git("for-each-ref", "--format=%(refname)", REF_PREFIX).splitlines() if line])


def pr_states() -> dict[int, dict]:
    proc = subprocess.run(
        [
            "gh", "pr", "list", "--state", "all", "--limit", "400",
            "--json", "number,state,isDraft,mergedAt,headRefOid",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    rows = json.loads(proc.stdout)
    return {int(row["number"]): row for row in rows}


def evidence_blobs(revs: list[str]) -> set[str]:
    out = git("rev-list", "--objects", *revs, "--", PURGE_PATH)
    return {line.split(" ", 1)[0] for line in out.splitlines() if line.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "audit").splitlines()[0])
    parser.add_argument("--fetch", action="store_true", help="mirror refs/pull/*/head first")
    parser.add_argument("--limit", type=int, default=0, help="inspect only the first N refs")
    parser.add_argument("--state", action="append", default=[], help="filter: OPEN|MERGED|CLOSED")
    args = parser.parse_args(argv)

    if args.fetch:
        print(f"mirrored {fetch_pr_refs()} pull-request refs into {REF_PREFIX}/*")

    refs = [line for line in git("for-each-ref", "--format=%(refname)", REF_PREFIX).splitlines() if line]
    if not refs:
        raise SystemExit(f"no {REF_PREFIX}/* refs; run with --fetch")
    if args.limit:
        refs = refs[: args.limit]

    states = pr_states()
    evidence = evidence_blobs(["refs/heads/master"])
    print(f"evidence blobs reachable from master: {len(evidence)}")
    print(f"pull-request refs under audit: {len(refs)}\n")

    rows: list[dict] = []
    for ref in refs:
        number = int(ref.rsplit("/", 1)[-1]) if ref.rsplit("/", 1)[-1].isdigit() else 0
        history = {
            line.split(" ", 1)[0]
            for line in git("rev-list", "--objects", ref, "--", PURGE_PATH).splitlines()
            if line.strip()
        }
        current = [
            line
            for line in git("ls-tree", "-r", "--name-only", ref, "--", PURGE_PATH).splitlines()
            if line.strip()
        ]
        state = states.get(number, {})
        rows.append(
            {
                "pr": number,
                "state": str(state.get("state") or "UNKNOWN"),
                "draft": bool(state.get("isDraft")),
                "merged": bool(state.get("mergedAt")),
                "head": state.get("headRefOid") or git("rev-parse", ref).strip(),
                "history_blobs": len(history),
                "tree_paths": len(current),
                "history_only": len(history) > 0 and len(current) == 0,
            }
        )

    if args.state:
        wanted = {s.upper() for s in args.state}
        rows = [row for row in rows if row["state"] in wanted]

    affected = [row for row in rows if row["history_blobs"]]
    hidden = [row for row in affected if row["history_only"]]
    by_state = Counter(row["state"] for row in affected)
    print(f"{'PR':>5}  {'state':<7} {'draft':<5} {'head':<10} {'hist blobs':>10} {'tree paths':>10}  note")
    for row in sorted(affected, key=lambda r: (r["state"], -r["history_blobs"])):
        note = "history-only" if row["history_only"] else "also in tree"
        print(
            f"{row['pr']:>5}  {row['state']:<7} {str(row['draft']):<5} {row['head'][:10]:<10} "
            f"{row['history_blobs']:>10} {row['tree_paths']:>10}  {note}"
        )

    print(f"\nrefs inspected: {len(rows)}")
    print(f"refs that can reach evidence blobs: {len(affected)}  {dict(by_state)}")
    print(f"of those, history-only (tree is clean): {len(hidden)}")
    print(f"stacked PRs a support request must dereference: {len(affected)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
