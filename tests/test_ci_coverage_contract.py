"""CI coverage contract (#224).

A green CI run cannot show either of the two ways a gate stops gating:

1. **a test file no job collects** — it can never fail CI, however many
   assertions it holds;
2. **a job missing from the aggregate `needs:` list** — its failure cannot
   block a merge, so it is a report, not a gate.

Both are made explicit and bounded here. The uncollected set is a **ratchet**:
it may shrink as files are wired in, never grow silently.
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

# Ratchet measured on 2026-09-10 (master a2034100 + this change): of 237 test
# files, 54 are collected across the three workflows and 183 are not. Wire a
# job in, or delete a duplicated file, to lower this; raise it only with a
# written reason, because every increment is a test that cannot fail CI.
UNCOLLECTED_TEST_FILES_MAX = 183

# Jobs that exist but cannot gate a merge, with the reason each may stay out of
# the aggregate. Anything else must be in `needs:`.
NON_REQUIRED_JOBS: dict[str, str] = {}


def _workflow(name: str) -> dict[str, Any]:
    """Parsed workflow mapping; the schema is checked by the assertions below."""
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


def _ci_targets() -> set[str]:
    """Test paths any workflow's pytest step actually collects."""
    targets: set[str] = set()
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        jobs: dict[str, Any] = _workflow(path.name).get("jobs") or {}
        for job in jobs.values():
            for step in (job or {}).get("steps") or []:
                script = step.get("run")
                if not isinstance(script, str) or "pytest" not in script:
                    continue
                for match in _PYTEST_ARGS.finditer(script):
                    for raw in re.split(r"[\s\\]+", match.group(1)):
                        token = raw.strip().strip("\"'")
                        if token.startswith("tests/") and (
                            token.endswith("/") or token.endswith(".py")
                        ):
                            targets.add(token)
    return targets


def _collected(files: set[str], targets: set[str]) -> set[str]:
    directories = {t for t in targets if t.endswith("/")}
    return {
        f for f in files if f in targets or any(f.startswith(d) for d in directories)
    }


class TestCITestCoverage:
    def test_no_test_file_falls_outside_ci(self):
        files = _all_test_files()
        uncollected = files - _collected(files, _ci_targets())
        assert len(uncollected) <= UNCOLLECTED_TEST_FILES_MAX, (
            f"{len(uncollected)} test files are collected by no CI job (ratchet "
            f"is {UNCOLLECTED_TEST_FILES_MAX}); a test CI never runs cannot fail "
            "a merge. Wire the new file into a job, or lower the ratchet in the "
            "same commit:\n  " + "\n  ".join(sorted(uncollected))
        )

    def test_ratchet_equals_the_real_count(self):
        """Keep the constant honest: a new uncollected file must trip the test
        above, which means progress must lower the constant in the same commit."""
        files = _all_test_files()
        uncollected = len(files - _collected(files, _ci_targets()))
        assert uncollected == UNCOLLECTED_TEST_FILES_MAX, (
            f"uncollected count is {uncollected} but the ratchet says "
            f"{UNCOLLECTED_TEST_FILES_MAX}: set it to {uncollected} (progress) "
            "or explain the increase"
        )

    def test_every_path_a_workflow_names_exists(self):
        """A renamed or deleted test must break CI loudly, not silently shrink it."""
        missing = sorted(t for t in _ci_targets() if not (REPO_ROOT / t).exists())
        assert not missing, f"workflows reference paths that do not exist: {missing}"

    def test_the_backend_boundary_check_is_wired(self):
        """The only Python gate that reads backend write scope must actually run."""
        targets = _ci_targets()
        assert "tests/test_architecture_boundaries.py" in targets


class TestAggregateGate:
    """`alls-green` is what branch protection reads; it must name every job."""

    WORKFLOWS: tuple[str, ...] = ("ci.yml",)

    @pytest.mark.parametrize("name", WORKFLOWS)
    def test_aggregate_needs_every_job(self, name: str):
        jobs: dict[str, Any] = _workflow(name)["jobs"]
        required = set(jobs["alls-green"].get("needs") or ())
        declared = set(jobs) - {"alls-green"}
        missing = declared - required - set(NON_REQUIRED_JOBS)
        assert not missing, (
            f"{name}: these jobs cannot block a merge because `alls-green` does "
            f"not need them: {sorted(missing)}"
        )
        unknown = required - declared
        assert not unknown, f"{name}: `needs` names unknown jobs: {sorted(unknown)}"

    @pytest.mark.parametrize("name", WORKFLOWS)
    def test_declared_non_required_jobs_carry_a_reason(self, name: str):
        declared = set(_workflow(name)["jobs"]) - {"alls-green"}
        for job, reason in NON_REQUIRED_JOBS.items():
            assert job in declared, f"{name}: {job} is not a job in this workflow"
            assert reason.strip(), f"{job} needs a written reason"


class TestLocalRunnerMirrorsCI:
    """`scripts/ci_local.py` must not silently drop a CI step.

    The pre-flight exists so a push is not the first time a gate runs; if its
    parser quietly skipped a step it would report confidence it did not earn —
    the same failure mode this whole file is about. Exercised through the CLI
    surface, not an internal function.
    """

    def _listed(self) -> list[dict]:
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
            if re.search(r"pip install|npm ci", json.dumps(e) + e["name"], re.I)
            or "Install" in str(e["name"])
        ]
        assert installs, "expected install steps to exist in the workflows"
        assert all(e["skipped"] for e in installs), (
            "a pre-flight must not mutate the environment unasked: "
            f"{[e for e in installs if not e['skipped']]}"
        )
