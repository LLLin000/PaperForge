"""CI coverage contract (#224, Block A: collection convergence).

A green CI run hides two ways a gate stops gating:

1. **a test file no gating job collects** — it can never fail a merge, however
   many assertions it holds;
2. **a job missing from the aggregate `needs:` list** — its failure cannot
   block a merge, so it is a report, not a gate.

Both are made explicit here. Coverage is expressed as a **registry of reasons**,
not a count: every test file is either collected by `ci.yml` (the merge gate) or
listed with the reason it is allowed to sit outside it. A new file with no
entry fails this contract, and a stale entry (a file that is now gated, or one
that no longer exists) fails too.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
TESTS_DIR = REPO_ROOT / "tests"

#: The merge gate. Only these workflows can block a pull request; a file
#: collected solely by a scheduled workflow is *not* gated.
GATING_WORKFLOW = "ci.yml"

#: Files the merge gate does not collect, each with the reason it may stay out.
#: Adding a file here is a claim that it need not gate; an empty reason fails.
EXCLUDED_UNGATED: dict[str, str] = {
    # Destructive by design; a weekly scheduled workflow owns them so a PR is
    # never the thing that eats a filesystem or a network quota.
    "tests/chaos/test_corrupted_inputs.py": "destructive; runs in the weekly Chaos workflow (ci-chaos.yml), not on PRs",
    "tests/chaos/test_filesystem_errors.py": "destructive; runs in the weekly Chaos workflow (ci-chaos.yml), not on PRs",
    "tests/chaos/test_network_failures.py": "destructive; runs in the weekly Chaos workflow (ci-chaos.yml), not on PRs",
}

#: Files a gating job *names* but a `-m` marker filter excludes, so they never
#: execute. Collected-on-paper is not gated; the assertion below also checks
#: each file still lacks the mark, so adding one forces this entry to go.
NOT_EXECUTED_DESPITE_COLLECTION: dict[str, str] = {
    "tests/e2e/test_legacy_ocr_backfill_smoke.py": (
        "inside tests/e2e/, which L4 runs with `-m e2e`, but the module has no "
        "`pytestmark`; it also needs a real legacy-layout vault and skips without "
        "one, so it cannot gate either way"
    ),
}


def _workflow(name: str) -> dict[str, Any]:
    """Parsed workflow mapping; the shape is checked by the assertions below."""
    return cast(
        "dict[str, Any]",
        yaml.safe_load((WORKFLOW_DIR / name).read_text(encoding="utf-8")),
    )


def _all_test_files() -> set[str]:
    return {
        p.relative_to(REPO_ROOT).as_posix()
        for p in TESTS_DIR.rglob("test_*.py")
        if "__pycache__" not in p.parts
    }


# A pytest invocation's arguments run until the first option flag. Taking the
# arguments (not every path-like string) matters: `tests/cli/test_x.py` is a
# file, while `tests/cli/` alone is a whole directory, and confusing the two
# hides every other file in that directory.
_PYTEST_ARGS = re.compile(r"(?:python -m pytest|pytest)\s+(.*?)(?=\s--?\w|\Z)", re.S)
_IGNORED = re.compile(r"--ignore[= ]\s*(tests/[\w/.\-]+)")
_MARKER_FILTER = re.compile(r"-m\s+['\"]?(\w+)")


def _pytest_steps(workflow_name: str) -> list[tuple[set[str], set[str]]]:
    """(targets, ignored) per pytest step.

    `--ignore` has to be parsed too: the full-suite job runs `pytest tests/`
    minus a few directories, and reading only the target would claim every file
    in the tree is gated.
    """
    steps: list[tuple[set[str], set[str]]] = []
    jobs: dict[str, Any] = _workflow(workflow_name).get("jobs") or {}
    for job in jobs.values():
        for step in (job or {}).get("steps") or []:
            script = step.get("run")
            if not isinstance(script, str) or "pytest" not in script:
                continue
            targets: set[str] = set()
            for match in _PYTEST_ARGS.finditer(script):
                for raw in re.split(r"[\s\\]+", match.group(1)):
                    token = raw.strip().strip("\"'")
                    if token.startswith("tests/") and (
                        token.endswith("/") or token.endswith(".py")
                    ):
                        targets.add(token)
            ignored = set()
            for raw in _IGNORED.findall(script):
                normalised = raw if raw.endswith("/") or raw.endswith(".py") else raw + "/"
                ignored.add(normalised)
            steps.append((targets, ignored))
    return steps


def _pytest_targets(workflow_name: str) -> set[str]:
    """Every path this workflow's pytest steps name (ignores not applied)."""
    return {target for targets, _ignored in _pytest_steps(workflow_name) for target in targets}


def _matches(path: str, entries: set[str]) -> bool:
    return path in entries or any(
        path.startswith(e) for e in entries if e.endswith("/")
    )


def _collects(targets: set[str], file: str) -> bool:
    return _matches(file, targets)


class TestCITestCoverage:
    def test_every_test_file_is_gated_or_declared(self):
        """A file no merge gate collects must carry a written reason."""
        files = _all_test_files()
        collected: set[str] = set()
        for targets, ignored in _pytest_steps(GATING_WORKFLOW):
            # Per step: a target only counts when that same invocation does not
            # exclude the path. Accumulating targets and ignores separately let
            # `pytest tests/ --ignore=tests/chaos` read as covering chaos.
            for f in files:
                if _matches(f, targets) and not _matches(f, ignored):
                    collected.add(f)
        ungated: set[str] = files - collected

        undeclared = sorted(ungated - set(EXCLUDED_UNGATED))
        assert not undeclared, (
            f"{len(undeclared)} test files are collected by no job in "
            f"{GATING_WORKFLOW}:\n  "
            + "\n  ".join(undeclared)
            + "\nWire them into a job, or add each to EXCLUDED_UNGATED with the "
            "reason it need not gate."
        )
        stale = sorted(set(EXCLUDED_UNGATED) - ungated)
        assert not stale, (
            f"EXCLUDED_UNGATED lists files that are no longer ungated (or no "
            f"longer exist): {stale}. Remove them — a stale exclusion is a "
            "claim about coverage that is no longer true."
        )

    def test_named_but_never_executed_files_are_declared(self):
        """A gating job that *names* a directory still runs `-m <marker>`.

        On paper the file is collected; in practice the filter drops it, so it
        is as ungated as an ignored one. The check is paired with the file's own
        mark: once the module gains `pytestmark`, the entry must go.
        """
        for path, reason in NOT_EXECUTED_DESPITE_COLLECTION.items():
            assert reason.strip(), f"{path} needs a written reason"
            source = (REPO_ROOT / path).read_text(encoding="utf-8")
            assert "pytestmark" not in source, (
                f"{path} now carries pytestmark, so the marker filter no longer "
                "drops it — remove the exemption"
            )

    def test_every_exclusion_states_a_reason(self):
        for path, reason in EXCLUDED_UNGATED.items():
            assert reason.strip(), f"{path} needs a written reason"
            assert (REPO_ROOT / path).is_file(), f"{path} does not exist"

    def test_every_path_a_workflow_names_exists(self):
        """A renamed or deleted test must break CI loudly, not silently shrink it."""
        missing = sorted(
            t
            for name in ("ci.yml", "ci-chaos.yml", "publish.yml", "pages.yml")
            if (WORKFLOW_DIR / name).exists()
            for t in _pytest_targets(name)
            if not (REPO_ROOT / t).exists()
        )
        assert not missing, f"workflows reference paths that do not exist: {missing}"

    def test_the_backend_boundary_check_is_wired(self):
        """The only Python gate that reads backend write scope must actually run."""
        assert "tests/test_architecture_boundaries.py" in _pytest_targets(
            GATING_WORKFLOW
        )

    def test_the_full_suite_job_runs_the_uncollected_tree(self):
        """The job that closes the coverage hole must still exist and run pytest."""
        jobs: dict[str, Any] = _workflow(GATING_WORKFLOW).get("jobs") or {}
        assert "python-suite" in jobs, (
            "the full-suite job was removed; without it, files outside "
            "tests/unit/ are gated by nothing"
        )
        scripts = " ".join(
            str(step.get("run") or "") for step in jobs["python-suite"].get("steps") or []
        )
        assert "pytest tests/" in scripts


class TestAggregateGate:
    """`alls-green` is what branch protection reads; it must name every job."""

    @pytest.mark.parametrize("name", [GATING_WORKFLOW])
    def test_aggregate_needs_every_job(self, name: str):
        jobs: dict[str, Any] = _workflow(name)["jobs"]
        required = set(jobs["alls-green"].get("needs") or ())
        declared = set(jobs) - {"alls-green"}
        missing = declared - required
        assert not missing, (
            f"{name}: these jobs cannot block a merge because `alls-green` does "
            f"not need them: {sorted(missing)}"
        )
        unknown = required - declared
        assert not unknown, f"{name}: `needs` names unknown jobs: {sorted(unknown)}"

    def test_architecture_gate_fails_closed(self):
        jobs: dict[str, Any] = _workflow(GATING_WORKFLOW)["jobs"]
        scripts = " ".join(
            str(step.get("run") or "")
            for step in jobs["architecture-gate"].get("steps") or []
        )
        assert "--strict" in scripts


class TestLocalRunnerMirrorsCI:
    """`scripts/ci_local.py` must not silently drop a CI step.

    The pre-flight exists so a push is not the first time a gate runs; if its
    parser quietly skipped a step it would report confidence it did not earn —
    the same failure mode this whole file is about. Exercised through the CLI
    surface, not an internal function.
    """

    def _listed(self) -> list[dict[str, Any]]:
        result = subprocess.run(
            [sys.executable, "scripts/ci_local.py", "--list", "--json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        return cast("list[dict]", json.loads(result.stdout))

    def test_every_run_step_is_represented(self):
        seen: dict[str, int] = {}
        for entry in self._listed():
            job = str(entry["job"])
            seen[job] = seen.get(job, 0) + 1

        for name in sorted(WORKFLOW_DIR.glob("*.yml")):
            jobs: dict = _workflow(name.name).get("jobs") or {}
            for job_name, job in jobs.items():
                expected = sum(
                    1
                    for raw in (job or {}).get("steps") or []
                    if isinstance((raw or {}).get("run"), str)
                )
                assert seen.get(job_name, 0) == expected, (
                    f"{name.name}:{job_name} has {expected} run steps but the "
                    f"local runner reports {seen.get(job_name, 0)}"
                )

    def test_install_steps_are_skipped_by_default(self):
        listed = self._listed()
        installs = [
            e
            for e in listed
            if re.search(r"pip install|npm ci", json.dumps(e) + str(e["name"]), re.I)
            or "Install" in str(e["name"])
        ]
        assert installs, "expected install steps to exist in the workflows"
        assert all(e["skipped"] for e in installs), (
            "a pre-flight must not mutate the environment unasked: "
            f"{[e for e in installs if not e['skipped']]}"
        )
