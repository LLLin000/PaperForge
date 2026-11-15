#!/usr/bin/env python3
"""Build and verify a purged clone of this repository — never the live one.

Two things are removed from history:

1. the whole ``docs/evidence/`` corpus (paper page/figure images and the JSON
   dumps that name real Zotero storage paths and paper identities);
2. the remaining machine paths, by literal replacement, so the products of the
   rewrite cannot simply reappear in tests, scripts or docs.

The clone is a ``--mirror`` in a scratch directory. Nothing is pushed, no ref in
the working repository is touched. The owner decides whether to force-push the
result; the script prints exactly what that costs (new commit ids, tag map).

Usage:
    python scripts/dev/history_purge.py --workdir D:/tmp/pf-purge
    python scripts/dev/history_purge.py --workdir D:/tmp/pf-purge --keep
"""
from __future__ import annotations

import argparse
import collections
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Subtrees that must not exist in any published history.
PURGE_PATHS: tuple[str, ...] = ("docs/evidence",)

#: Literal replacements applied to every text blob in history. The left-hand
#: sides are assembled from fragments so this file itself carries no machine
#: path — otherwise the rewrite would rewrite its own replacement table.
_USER = "".join(["L", "in"])
_ROOT = "".join(["D:", "/", "L", "/"])
_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("C:/Users/" + _USER, "<home>"),
    ("C:\\Users\\" + _USER, "<home>"),
    ("c:/users/" + _USER.lower(), "<home>"),
    ("c:\\users\\" + _USER.lower(), "<home>"),
    ("/Users/" + _USER, "<home>"),
    (_ROOT, "<root>/"),
    (_ROOT.replace("/", "\\"), "<root>\\"),
    (_ROOT.lower(), "<root>/"),
    (_ROOT.lower().replace("/", "\\"), "<root>\\"),
    ("<programs>/", "<programs>/"),
    ("D:\\programs\\", "<programs>\\"),
)
REPLACEMENTS = _REPLACEMENTS

#: Same identities the repository checker looks for, assembled from the same
#: fragments so the verification pass survives the rewrite it verifies.
_VERIFY_USER = "".join(["L", "in"])
_MARKER_FRAGMENTS: tuple[tuple[str, str], ...] = (
    ("windows-home", "C:/Users/" + _VERIFY_USER),
    ("windows-home-bs", "C:\\Users\\" + _VERIFY_USER),
    ("posix-home", "/Users/" + _VERIFY_USER),
    ("projects-drive", "D:" + "/L/"),
    ("projects-drive-bs", "D:" + "\\L\\"),
)
MARKERS: tuple[tuple[str, str], ...] = _MARKER_FRAGMENTS


def git(*args: str, cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def run(cmd: list[str], cwd: Path) -> str:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip()[-4000:] or f"{cmd[0]} failed")
    return proc.stdout + proc.stderr


def blob_markers(clone: Path, limit_bytes: int = 1_000_000, revs: list[str] | None = None) -> dict[str, int]:
    """Count leftover machine identities across every text blob, streamed.

    Binary blobs (images) are skipped by size; the strings cannot live there.
    Reading through one ``cat-file --batch`` stream keeps memory flat.
    """
    if revs:
        # Only the objects a normal push publishes. A `git push --mirror`
        # would also carry refs/stash and refs/codex/*, whose old blobs are
        # deliberately not part of the release surface.
        listing = git("rev-list", "--objects", *revs, cwd=clone)
        candidates = {row.split()[0] for row in listing.splitlines() if row.strip()}
        meta = run(
            ["git", "-C", str(clone), "cat-file", "--batch-all-objects",
             "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
            cwd=clone,
        )
        targets = [
            row.split()[0]
            for row in meta.splitlines()
            if len(row.split()) == 3
            and row.split()[1] == "blob"
            and int(row.split()[2]) <= limit_bytes
            and row.split()[0] in candidates
        ]
    else:
        listing = git(
            "cat-file", "--batch-all-objects",
            "--batch-check=%(objectname) %(objecttype) %(objectsize)",
            cwd=clone,
        )
        targets = [
            row.split()[0]
            for row in listing.splitlines()
            if len(row.split()) == 3 and row.split()[1] == "blob" and int(row.split()[2]) <= limit_bytes
        ]
    if not targets:
        return {}
    found: collections.Counter[str] = collections.Counter()
    needles = [(name, text.encode("utf-8")) for name, text in MARKERS]
    proc = subprocess.Popen(
        ["git", "-C", str(clone), "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None and proc.stdout is not None
    for sha in targets:
        proc.stdin.write(sha.encode() + b"\n")
    proc.stdin.close()
    while True:
        header = proc.stdout.readline()
        if not header:
            break
        parts = header.split()
        if len(parts) < 3:
            continue
        size = int(parts[2])
        payload = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing newline
        for name, needle in needles:
            count = payload.count(needle)
            if count:
                found[name] += count
    proc.wait()
    return dict(found)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "purge").splitlines()[0])
    parser.add_argument("--workdir", required=True, help="scratch directory for the mirror clone")
    parser.add_argument("--keep", action="store_true", help="leave the rewritten clone on disk")
    args = parser.parse_args(argv)

    workdir = Path(args.workdir)
    clone = workdir / "repo.git"
    workdir.mkdir(parents=True, exist_ok=True)
    if clone.exists():
        raise SystemExit(f"{clone} already exists; remove it or pick another --workdir")

    print(f"mirroring {REPO_ROOT} -> {clone}")
    git("clone", "--mirror", str(REPO_ROOT), str(clone), cwd=REPO_ROOT)

    before_commits = int(git("rev-list", "--count", "--all", cwd=clone).strip())
    before_size = run(["git", "-C", str(clone), "count-objects", "-vH"], cwd=clone)
    before_pack = next((ln for ln in before_size.splitlines() if ln.startswith("size-pack")), "size-pack: ?")
    before_tags = [line for line in git("tag", cwd=clone).splitlines() if line]
    before_master = git("rev-parse", "refs/heads/master", cwd=clone).strip()

    exprs = workdir / "replacements.txt"
    exprs.write_text("\n".join(f"{old}==>{new}" for old, new in REPLACEMENTS) + "\n", encoding="utf-8")
    print(f"applying {len(REPLACEMENTS)} literal replacement(s) and purging {len(PURGE_PATHS)} path root(s)")

    filter_repo = shutil_which("git-filter-repo")
    cmd = [filter_repo, "--invert-paths", "--force", "--replace-text", str(exprs)]
    for path in PURGE_PATHS:
        cmd += ["--path", path]
    print(run(cmd, cwd=clone).strip().splitlines()[-1])

    after_commits = int(git("rev-list", "--count", "--all", cwd=clone).strip())
    after_size = run(["git", "-C", str(clone), "count-objects", "-vH"], cwd=clone)
    after_pack = next((ln for ln in after_size.splitlines() if ln.startswith("size-pack")), "size-pack: ?")
    after_master = git("rev-parse", "refs/heads/master", cwd=clone).strip()
    residue = git("rev-list", "--objects", "--all", "--", *PURGE_PATHS, cwd=clone).strip()
    markers = blob_markers(clone, revs=["--branches", "--tags", "--remotes"])
    other_refs = [
        ref
        for ref in git("for-each-ref", "--format=%(refname)", cwd=clone).splitlines()
        if not ref.startswith(("refs/heads/", "refs/tags/", "refs/remotes/"))
    ]
    other_hits = blob_markers(clone) if other_refs else {}

    tags_after = {
        tag: git("rev-parse", f"refs/tags/{tag}", cwd=clone).strip()
        for tag in before_tags
    }
    tags_before = {
        tag: git("rev-parse", f"refs/tags/{tag}", cwd=REPO_ROOT).strip() for tag in before_tags
    }

    print("\n=== result ===")
    print(f"commits        {before_commits} -> {after_commits}")
    print(f"{before_pack} -> {after_pack}")
    print(f"master         {before_master[:12]} -> {after_master[:12]}")
    print(f"purged paths   {'still present: ' + residue.splitlines()[0] if residue else 'no object remains'}")
    print(f"machine blobs  {markers or 'none'} (branches/tags/remotes only)")
    if other_refs:
        print(f"other refs     {', '.join(other_refs[:4])} — {other_hits or 'clean'}; never `git push --mirror`")
    changed = [tag for tag in tags_after if tags_after[tag] != tags_before.get(tag)]
    print(f"tags moved     {len(changed)}/{len(tags_after)}: {', '.join(changed) if changed else '-'}")

    mapping = workdir / "ref-mapping.txt"
    lines = [f"master {before_master} {after_master}"]
    for tag in sorted(tags_after):
        lines.append(f"tag {tag} {tags_before.get(tag, '-')} {tags_after[tag]}")
    for ref in git("for-each-ref", "--format=%(refname) %(objectname)", cwd=clone).splitlines():
        lines.append(f"ref {ref}")
    mapping.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"mapping written {mapping}")

    if markers:
        print("\nREFUSING: markers survive the rewrite", file=sys.stderr)
        return 1
    if args.keep:
        print(f"\nkept for inspection: {clone}")
    else:
        import shutil

        shutil.rmtree(clone, ignore_errors=True)
        print(f"\nremoved {clone} (pass --keep to inspect it)")
    return 0


def shutil_which(name: str) -> str:
    from shutil import which

    found = which(name) or which(name + ".exe")
    if not found:
        raise SystemExit(f"{name} not found on PATH")
    return found


if __name__ == "__main__":
    sys.exit(main())
