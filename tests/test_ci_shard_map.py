"""The CI shard map must stay a partition of the suite.

`scripts/ci_shard.py` splits the full-suite job; if a new test file is added
without regenerating `tests/ci-shards.json`, that file is collected by no CI
job and gating silently stops. This test is the guard: it fails with the exact
command to run.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "tests" / "ci-shards.json"


def _tracked() -> set[str] | None:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", "tests"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return {path for path in proc.stdout.split("\0") if path}


def _suite_files() -> set[str]:
    tracked = _tracked()
    return {
        p.relative_to(REPO_ROOT).as_posix()
        for p in (REPO_ROOT / "tests").rglob("test_*.py")
        if "__pycache__" not in p.parts
        and (tracked is None or p.relative_to(REPO_ROOT).as_posix() in tracked)
        and not p.relative_to(REPO_ROOT).as_posix().startswith(
            ("tests/e2e/", "tests/audit/", "tests/chaos/", "tests/harness/")
        )
    }


def _map() -> dict[str, int]:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))["files"]


def test_map_covers_every_suite_file() -> None:
    mapping = _map()
    missing = sorted(_suite_files() - set(mapping))
    assert not missing, (
        "tests/ci-shards.json does not assign these files to a shard; run "
        "`python scripts/ci_shard.py --write` and commit the result:\n  "
        + "\n  ".join(missing)
    )


def test_map_names_no_stale_file() -> None:
    stale = sorted(set(_map()) - _suite_files())
    assert not stale, (
        "tests/ci-shards.json lists files that no longer exist; run "
        "`python scripts/ci_shard.py --write`:\n  " + "\n  ".join(stale)
    )


def test_shard_indices_are_in_range() -> None:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    shard_count = int(data["shards"])
    expected = set(range(shard_count))
    indices = set(data["files"].values())
    assert indices <= expected, f"unexpected shard indices: {sorted(indices)}"
    assert indices == expected, "one or more shards are empty; rebalance the map"


def test_shards_are_balanced_by_file_count() -> None:
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    shard_count = int(data["shards"])
    counts = {i: 0 for i in range(shard_count)}
    for shard in data["files"].values():
        counts[shard] += 1
    small, large = min(counts.values()), max(counts.values())
    assert large - small <= max(10, large * 0.1), (
        f"shards are lopsided: {counts}; regenerate with `--write --of {shard_count}`"
    )
