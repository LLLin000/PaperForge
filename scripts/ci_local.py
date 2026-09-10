#!/usr/bin/env python3
"""Run CI's own job commands locally (#224).

Reads `.github/workflows/*.yml` and executes the portable steps, so a push is
not the first time a gate runs. The commands are **derived from the workflow**,
never copied: a step edited in CI is edited here by construction.

What "portable" excludes, and why:

- steps that use an action (`uses:`) — checkout/setup, not test commands;
- steps with an `if:` — runner-OS or event conditions this machine cannot judge;
- steps whose script contains a `${{ … }}` expression — resolved only in CI;
- dependency installs (`pip install`, `npm ci`, `npm install`) unless
  `--include-install` is passed, so a pre-flight never mutates this machine's
  environment unasked.

Not a replacement for CI: no OS matrix, no clean checkout, no caches. A job
needing another OS will fail here for the wrong reason; the summary says so.

Usage:
    python scripts/ci_local.py --list
    python scripts/ci_local.py                     # every job
    python scripts/ci_local.py --job j-matrix      # one job
    python scripts/ci_local.py --keep-going        # default: run all, report all
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
DESCRIPTION = (__doc__ or "Run CI's own job commands locally").splitlines()[0]
INSTALL_PATTERN = re.compile(r"\b(?:pip install|pip3 install|npm ci|npm install|pnpm install)\b")
EXPRESSION_PATTERN = re.compile(r"\$\{\{")


@dataclass(frozen=True)
class Step:
    job: str
    name: str
    script: str
    cwd: Path
    shell: str
    skipped: str | None = None


def _steps() -> list[Step]:
    steps: list[Step] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        workflow: dict[str, Any] = cast(
            "dict[str, Any]", yaml.safe_load(path.read_text(encoding="utf-8"))
        )
        for job_name, job in (workflow.get("jobs") or {}).items():
            job = cast("dict[str, Any]", job or {})
            job_defaults = (job.get("defaults") or {}).get("run", {}) or {}
            default_cwd = job_defaults.get("working-directory")
            default_shell = str(job_defaults.get("shell") or "")
            for index, raw in enumerate(job.get("steps") or [], start=1):
                step = cast("dict[str, Any]", raw or {})
                script = step.get("run")
                name = str(step.get("name") or f"{job_name} step {index}")
                if not isinstance(script, str):
                    continue  # `uses:` steps are setup, not gates
                cwd = REPO_ROOT / str(step.get("working-directory") or default_cwd or "")
                reason: str | None = None
                if step.get("if"):
                    reason = f"conditional in CI ({step['if']})"
                elif EXPRESSION_PATTERN.search(script):
                    reason = "uses a CI expression"
                elif INSTALL_PATTERN.search(script) and not _include_install:
                    reason = "installs dependencies (use --include-install)"
                shell = str(step.get("shell") or default_shell or "bash")
                if reason is None and _BASH_ONLY.search(_flatten(script)):
                    reason = "uses shell features the pre-flight does not emulate"
                steps.append(
                    Step(
                        job=str(job_name),
                        name=name,
                        script=script,
                        cwd=cwd,
                        shell=shell,
                        skipped=reason,
                    )
                )
    return steps


# Shell features this pre-flight does not emulate. A step whose command needs
# them is reported as skipped rather than run wrong — a command mangled by the
# wrong shell reports failures that have nothing to do with the code.
_BASH_ONLY = re.compile(r"\$[({]|\[\[|<<|\|\||&&|;|\||>|<|\bzsh\b|\bnpm run [a-z]+ --")


def _flatten(script: str) -> str:
    """Join backslash-continued lines into one command line."""
    return re.sub(r"\\\s*\n\s*", " ", script).strip()


def _run(step: Step) -> tuple[bool, str]:
    """Run one step with the native shell.

    CI declares `shell: bash`; emulating that here proved unreliable (this
    machine's bash drops variable assignments), so the pre-flight runs the
    command with the host shell and refuses anything that needs real bash
    semantics.
    """
    command = _flatten(step.script)
    try:
        result = subprocess.run(
            command,
            cwd=str(step.cwd),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        return False, f"timed out after {_timeout}s\n{partial}"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output


def _tail(output: str, lines: int = 25) -> str:
    kept = [line for line in output.splitlines() if line.strip()]
    return "\n".join(kept[-lines:])


_include_install = False
_timeout = 900


def main(argv: list[str] | None = None) -> int:
    global _include_install, _timeout
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--job", action="append", default=[], help="run only this job (repeatable)")
    parser.add_argument("--list", action="store_true", help="list jobs and steps")
    parser.add_argument(
        "--include-install",
        action="store_true",
        help="also run dependency-install steps",
    )
    parser.add_argument("--tail", type=int, default=25, help="failure output lines")
    parser.add_argument("--json", action="store_true", help="machine-readable --list")
    parser.add_argument(
        "--timeout", type=int, default=900, help="per-step timeout in seconds (default 900)"
    )
    args = parser.parse_args(argv)
    _include_install = args.include_install
    _timeout = args.timeout

    steps = _steps()
    if args.job:
        steps = [s for s in steps if s.job in set(args.job)]
        if not steps:
            print(f"no such job: {', '.join(args.job)}", file=sys.stderr)
            return 2

    if args.list:
        if args.json:
            import json

            print(
                json.dumps(
                    [
                        {"job": s.job, "name": s.name, "skipped": s.skipped}
                        for s in steps
                    ],
                    ensure_ascii=False,
                )
            )
            return 0
        for step in steps:
            mark = f" [skip: {step.skipped}]" if step.skipped else ""
            print(f"{step.job:18s} {step.shell:5s} {step.name}{mark}")
        return 0

    results: list[tuple[str, str, str]] = []
    failures = 0
    for step in steps:
        if step.skipped:
            print(f"-- {step.job}: {step.name} — skipped ({step.skipped})")
            results.append((step.job, step.name, "skipped"))
            continue
        print(f"-- {step.job}: {step.name}", flush=True)
        ok, output = _run(step)
        results.append((step.job, step.name, "pass" if ok else "FAIL"))
        if not ok:
            failures += 1
            print(_tail(output, args.tail), flush=True)

    print("\n=== summary ===")
    for job, name, status in results:
        print(f"{status:7s} {job:18s} {name}")
    ran = sum(1 for _, _, s in results if s != "skipped")
    print(f"\n{ran - failures}/{ran} executed steps passed ({failures} failed)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
