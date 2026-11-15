#!/usr/bin/env python3
"""Audit every ref GitHub publishes, by whether it can reach the evidence corpus.

Read-only. Nothing is deleted, pushed, retagged or rewritten; remote refs are
mirrored into a private namespace with explicit refspecs so no
``remote.origin.fetch`` entry is ever added.

Branches and tags matter as much as pull-request refs: a branch that still
points at an evidence commit keeps the blobs reachable no matter how clean
``master`` is afterwards.

Usage:
    python scripts/dev/ref_reachability_audit.py --fetch        # mirror refs
    python scripts/dev/ref_reachability_audit.py --report out.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PURGE_PATH = "docs/evidence"
NAMESPACE = "refs/audit"

#: remote ref prefix -> local mirror prefix, all fetched in one transaction.
MIRRORS = (
    ("refs/heads/", f"{NAMESPACE}/heads/"),
    ("refs/tags/", f"{NAMESPACE}/tags/"),
    ("refs/pull/", f"{NAMESPACE}/pull/"),
)


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


def git_stdin(stdin: str, *args: str) -> str:
    """Run git with a payload on stdin (argv limits are ~32k on Windows)."""
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def remote_refs() -> dict[str, str]:
    """Authoritative ref list straight from GitHub (no local guessing)."""
    out = git("ls-remote", "origin")
    refs: dict[str, str] = {}
    for line in out.splitlines():
        sha, _, name = line.partition("\t")
        if name:
            refs[name.strip()] = sha.strip()
    return refs


def fetch_all(refs: dict[str, str]) -> None:
    spec = []
    for prefix, local in MIRRORS:
        if prefix == "refs/pull/":
            spec.append(f"+{prefix}*/head:{local}*/head")
            spec.append(f"+{prefix}*/merge:{local}*/merge")
        else:
            spec.append(f"+{prefix}*:{local}*")
    git("fetch", "--quiet", "--no-tags", "origin", *spec)
    del refs  # the fetch uses the refspecs above; the caller re-reads locally


def local_refs() -> dict[str, str]:
    out = git("for-each-ref", "--format=%(refname) %(objectname)", NAMESPACE)
    refs: dict[str, str] = {}
    for line in out.splitlines():
        name, _, sha = line.partition(" ")
        if name and sha:
            refs[name.strip()] = sha.strip()
    return refs


def evidence_blobs(ref: str) -> list[str]:
    """Evidence **blobs** reachable from *ref*.

    `rev-list --objects` also prints commits, trees and (for annotated tags) the
    tag object itself; counting those inflated an earlier audit. Only lines
    whose recorded path is inside the purge root are evidence, and only blobs
    carry the content — verify the type instead of trusting the listing.
    """
    out = git("rev-list", "--objects", ref, "--", PURGE_PATH)
    shas = []
    for line in out.splitlines():
        sha, _, path = line.partition(" ")
        if not sha or not path.startswith(PURGE_PATH + "/"):
            continue
        shas.append(sha)
    if not shas:
        return []
    check = git_stdin("\n".join(shas) + "\n", "cat-file", "--batch-check=%(objectname) %(objecttype)")
    return [
        row.split()[0]
        for row in check.splitlines()
        if len(row.split()) == 2 and row.split()[1] == "blob"
    ]


def current_paths(ref: str) -> int:
    out = git("ls-tree", "-r", "--name-only", ref, "--", PURGE_PATH)
    return len([line for line in out.splitlines() if line.strip()])


def classify(name: str) -> tuple[str, str]:
    """(kind, label) for a mirrored ref name."""
    if name.startswith(f"{NAMESPACE}/heads/"):
        return "branch", name[len(f"{NAMESPACE}/heads/"):]
    if name.startswith(f"{NAMESPACE}/tags/"):
        return "tag", name[len(f"{NAMESPACE}/tags/"):]
    rest = name[len(f"{NAMESPACE}/pull/"):]
    number, _, kind = rest.partition("/")
    return f"pr-{kind}", number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "audit").splitlines()[1])
    parser.add_argument("--fetch", action="store_true", help="mirror every remote ref first")
    parser.add_argument("--report", default="", help="write the full finding list as JSON")
    parser.add_argument("--all", action="store_true", help="also print clean refs")
    args = parser.parse_args(argv)

    if args.fetch:
        fetched = remote_refs()
        print(f"remote refs advertised by origin: {len(fetched)}")
        fetch_all(fetched)

    refs = local_refs()
    if not refs:
        raise SystemExit(f"no {NAMESPACE}/* refs; run with --fetch")

    rows = []
    for name in sorted(refs):
        kind, label = classify(name)
        blobs = evidence_blobs(name)
        if not blobs and not args.all:
            continue
        rows.append(
            {
                "kind": kind,
                "ref": label,
                "mirror": name,
                "sha": refs[name],
                "history_blobs": len(blobs),
                "tree_paths": current_paths(name),
                "sample_blobs": blobs[:5],
            }
        )

    by_kind: dict[str, list[dict]] = {}
    for row in rows:
        by_kind.setdefault(row["kind"], []).append(row)
    totals: dict[str, int] = {}
    for kind in {classify(name)[0] for name in refs}:
        totals[kind] = sum(1 for name in refs if classify(name)[0] == kind)

    print(f"{'ref type':<10} {'total':>6} {'affected':>9}  treatment")
    treatments = {
        "branch": "delete or rewrite after authorisation",
        "tag": "history rewrite",
        "pr-head": "GitHub Support dereference",
        "pr-merge": "GitHub Support (synthetic ref)",
    }
    for kind in sorted(totals):
        affected = len(by_kind.get(kind, []))
        print(f"{kind:<10} {totals[kind]:>6} {affected:>9}  {treatments.get(kind, '-')}")

    for kind in sorted(by_kind):
        print(f"\n--- {kind} ({len(by_kind[kind])} affected) ---")
        for row in sorted(by_kind[kind], key=lambda r: -r["history_blobs"]):
            print(
                f"  {row['ref']:<34} {row['sha'][:10]} blobs={row['history_blobs']:<5} "
                f"tree={row['tree_paths']}"
            )

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"purge_path": PURGE_PATH, "totals": totals, "refs": rows}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nreport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
