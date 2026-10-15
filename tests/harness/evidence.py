"""Structured acceptance evidence for the CLI-host harness.

The project's real-machine verification standard binds every capability claim to
evidence that names its runner kind, host profile and source revision.  Before
this module the only runner producing such records was H (real Obsidian +
WebDriver), which is why cases had to be host-bound to be evidence-bound.

``CaseEvidence`` writes the same fields for a plain CLI run, so moving a case off
H keeps its evidence: one JSON file per case plus a run index a per-area report
can cite instead of a hand-maintained table.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

RUNNER_KIND = "harness_cli"
REPO_ROOT = Path(__file__).resolve().parents[2]

_MAX_TAIL = 4000


def evidence_root() -> Path:
    """Where case records land (``PF_EVIDENCE_DIR`` overrides; CI uploads it)."""
    override = os.environ.get("PF_EVIDENCE_DIR", "").strip()
    root = Path(override) if override else REPO_ROOT / "tests" / "evidence" / "cli-acceptance"
    root.mkdir(parents=True, exist_ok=True)
    return root


def source_sha() -> str:
    """The revision the evidence is bound to; empty when git is unavailable."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def host_profile() -> dict[str, str]:
    return {
        "runner_kind": RUNNER_KIND,
        "os": platform.system(),
        "os_release": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "executable": sys.executable,
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(
    root: Path, suffixes: tuple[str, ...] = (".md", ".json", ".jsonl")
) -> dict[str, str]:
    """Content digests of every file under ``root`` (sorted, relative keys)."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in suffixes:
            out[path.relative_to(root).as_posix()] = digest(path)
    return out


class CaseEvidence:
    """One acceptance case's record: commands, assertions, artifacts, verdict."""

    def __init__(
        self,
        case_id: str,
        title: str,
        *,
        host_spec_case: str = "",
        host: str = "cli",
    ) -> None:
        self.case_id = case_id
        self.title = title
        self.host = host
        self.host_spec_case = host_spec_case
        self.started_at = time.time()
        self.commands: list[dict[str, Any]] = []
        self.assertions: list[dict[str, Any]] = []
        self.artifacts: dict[str, str] = {}
        self.failure = ""

    # ── recording ───────────────────────────────────────────────────────
    def command(
        self,
        argv: list[str],
        *,
        returncode: int,
        duration_ms: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.commands.append(
            {
                "argv": argv,
                "returncode": returncode,
                "duration_ms": duration_ms,
                "stdout_tail": stdout[-_MAX_TAIL:],
                "stderr_tail": stderr[-_MAX_TAIL:],
            }
        )

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        """Record one assertion; the first failure names the case's verdict."""
        self.assertions.append({"name": name, "ok": bool(ok), "detail": detail[:2000]})
        if not ok and not self.failure:
            self.failure = name if not detail else f"{name}: {detail}"[:2000]

    def artifact(self, name: str, path: Path) -> None:
        if path.is_file():
            self.artifacts[name] = digest(path)
        elif path.is_dir():
            for key, value in tree_digest(path).items():
                self.artifacts[f"{name}/{key}"] = value

    # ── output ──────────────────────────────────────────────────────────
    def payload(self) -> dict[str, Any]:
        failed = [row for row in self.assertions if not row["ok"]]
        return {
            "case_id": self.case_id,
            "title": self.title,
            "host": self.host,
            "host_spec_case": self.host_spec_case,
            "runner_kind": RUNNER_KIND,
            "source_sha": source_sha(),
            "host_profile": host_profile(),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(self.started_at)),
            "duration_ms": int((time.time() - self.started_at) * 1000),
            "status": "VERIFIED" if not failed else "FAILED",
            "failure": self.failure,
            "assertions": self.assertions,
            "commands": self.commands,
            "artifacts": self.artifacts,
        }

    def write(self, root: Path | None = None) -> Path:
        target = (root or evidence_root()) / f"{self.case_id}.json"
        target.write_text(
            json.dumps(self.payload(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target


def write_index(records: list[Path], root: Path | None = None) -> Path:
    """Run index: a per-area report cites this instead of a hand-kept table."""
    base = root or evidence_root()
    rows = []
    for path in records:
        try:
            rows.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    index = {
        "runner_kind": RUNNER_KIND,
        "source_sha": source_sha(),
        "host_profile": host_profile(),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime()),
        "cases": [
            {
                "case_id": row.get("case_id"),
                "status": row.get("status"),
                "duration_ms": row.get("duration_ms"),
                "host_spec_case": row.get("host_spec_case"),
                "failure": row.get("failure"),
            }
            for row in sorted(rows, key=lambda item: str(item.get("case_id")))
        ],
    }
    target = base / "index.json"
    target.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
