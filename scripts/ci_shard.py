"""Deterministic shard selector for the Python suite (CI only).

The full suite is throughput-bound: ~3.8k tests, and no single case dominates.
Splitting it into two jobs halves the wall clock without a new dependency and
without the shared-state risk of parallel test execution inside one process.

`tests/ci-shards.json` is the map. It is regenerated on demand:

    python scripts/ci_shard.py --write

and `tests/test_ci_shard_map.py` fails when a test file is missing from it, so
the map cannot silently rot.

Usage in CI:

    pytest $(python scripts/ci_shard.py --shard 0 --of 2) ...
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "tests" / "ci-shards.json"

#: Directories another job owns; mirrors the full-suite job's --ignore list.
EXCLUDED_PREFIXES = (
    "tests/e2e/",
    "tests/audit/",
    "tests/chaos/",
    "tests/harness/",
)


def _tracked_test_files() -> set[str] | None:
    """Files git knows about; CI only ever sees the committed tree.

    Local-only test files (``.git/info/exclude``) must not enter the map: CI
    would report them as vanished and fail every shard.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "tests"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return {path for path in proc.stdout.split("\0") if path}


def suite_files() -> list[str]:
    """Every test file the full-suite job runs."""
    tracked = _tracked_test_files()
    return sorted(
        p.relative_to(REPO_ROOT).as_posix()
        for p in (REPO_ROOT / "tests").rglob("test_*.py")
        if "__pycache__" not in p.parts
        and (tracked is None or p.relative_to(REPO_ROOT).as_posix() in tracked)
        and not any(
            p.relative_to(REPO_ROOT).as_posix().startswith(pre)
            for pre in EXCLUDED_PREFIXES
        )
    )


def _collected_counts() -> dict[str, int]:
    """Test count per file, from pytest's own collection."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--collect-only",
            "-q",
            "--ignore=tests/e2e",
            "--ignore=tests/audit",
            "--ignore=tests/chaos",
            "--ignore=tests/harness",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout[-2000:] + proc.stderr[-2000:])
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        if "::" in line and line.startswith("tests/"):
            counts[line.split("::")[0]] = counts.get(line.split("::")[0], 0) + 1
    return counts


def write_map(shards: int) -> int:
    """Balance files across shards (greedy LPT on collected test counts)."""
    files = suite_files()
    allowed = set(files)
    counts = {file: count for file, count in _collected_counts().items() if file in allowed}
    # Helper modules match test_*.py but collect nothing; pin them to a shard
    # anyway so the map stays a partition of the tree.
    for file in files:
        counts.setdefault(file, 0)
    load = {i: 0 for i in range(shards)}
    assigned: dict[str, int] = {}
    for file, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        target = min(load, key=lambda i: (load[i], i))
        assigned[file] = target
        load[target] += count
    MAP_PATH.write_text(
        json.dumps({"shards": shards, "files": assigned}, indent=1) + "\n",
        encoding="utf-8",
    )
    print("shard sizes (tests):", dict(load), "total", sum(load.values()))
    return 0


def select(shard: int, of: int, args_file: str | None = None) -> int:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    mapping: dict[str, int] = data["files"]
    stale = sorted(set(suite_files()) - set(mapping))
    extra = sorted(set(mapping) - set(suite_files()))
    if stale or extra:
        print(
            "tests/ci-shards.json is stale; run `python scripts/ci_shard.py --write`\n"
            f"  unassigned: {stale[:5]}{'…' if len(stale) > 5 else ''}\n"
            f"  vanished:   {extra[:5]}{'…' if len(extra) > 5 else ''}",
            file=sys.stderr,
        )
        return 2
    files = sorted(f for f, s in mapping.items() if s == shard)
    missing = [f for f in files if not (REPO_ROOT / f).is_file()]
    if missing:
        print(
            "selected files are missing from the checkout: " + ", ".join(missing[:5]),
            file=sys.stderr,
        )
        return 2
    if args_file:
        # One path per line, handed to pytest as `@file`: a 120-path command
        # substitution is exactly how a Windows shell corrupts one argument.
        Path(args_file).write_text("\n".join(files) + "\n", encoding="utf-8")
        print(f"@{args_file}")
    else:
        print(" ".join(files))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="regenerate the map")
    parser.add_argument("--of", type=int, default=None, help="shard count")
    parser.add_argument("--shard", type=int, default=None, help="this shard index")
    parser.add_argument(
        "--args-file",
        default=None,
        metavar="PATH",
        help="write the shard as a pytest @argfile and print a single '@path' token",
    )
    args = parser.parse_args(argv)
    if args.write:
        return write_map(args.of or 2)
    if args.shard is None or args.of is None:
        parser.error("--shard and --of are required unless --write is passed")
    return select(args.shard, args.of, args.args_file)


if __name__ == "__main__":
    raise SystemExit(main())
