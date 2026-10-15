"""Real-CLI invocation with the evidence hook attached.

Every call records argv, exit code, duration and output tails into the case's
evidence record, so a failing case ships the exact command that failed instead
of a screenshot of a view that rendered the consequence.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .evidence import REPO_ROOT, CaseEvidence

STOP_TOKEN = "PAPERFORGE_STOP\n"
_TERMINALS = ("result", "error", "cancelled")


class CliResult:
    """One finished CLI call."""

    __slots__ = ("argv", "returncode", "stdout", "stderr", "duration_ms", "payload")

    def __init__(
        self,
        argv: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
    ) -> None:
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration_ms = duration_ms
        self.payload = self._parse(stdout)

    @staticmethod
    def _parse(stdout: str) -> Any:
        """Whatever JSON the command printed — a PFResult envelope or a bare list.

        `ocr list --json` prints a bare array, so refusing non-objects here
        would silently turn a populated table into "no rows".
        """
        text = stdout.strip()
        if not text or text[0] not in "{[":
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @property
    def data(self) -> Any:
        payload = self.payload
        return payload.get("data") if isinstance(payload, dict) else None

    def tail(self, limit: int = 400) -> str:
        return (self.stderr or self.stdout).strip()[-limit:]


class StreamRun:
    """A streamed (NDJSON) call, optionally ended by a cooperative stop."""

    __slots__ = ("argv", "events", "returncode", "duration_ms", "stopped", "expired", "stderr")

    def __init__(
        self,
        argv: list[str],
        events: list[dict[str, Any]],
        returncode: int,
        duration_ms: int,
        stopped: bool,
        expired: bool,
        stderr: str,
    ) -> None:
        self.argv = argv
        self.events = events
        self.returncode = returncode
        self.duration_ms = duration_ms
        self.stopped = stopped
        self.expired = expired
        self.stderr = stderr

    @property
    def terminal(self) -> dict[str, Any] | None:
        for event in reversed(self.events):
            if event.get("event") in _TERMINALS:
                return event
        return None

    def phases(self) -> list[str]:
        return [str(event.get("phase", "")) for event in self.events if event.get("event") == "phase"]


class CliHost:
    """`paperforge` driven the way the plugin drives it: one subprocess per call."""

    def __init__(
        self,
        vault: Path,
        case: CaseEvidence,
        *,
        timeout_s: int = 240,
        python: str | None = None,
        env_extra: dict[str, str] | None = None,
    ) -> None:
        self.vault = Path(vault)
        self.case = case
        self.timeout_s = timeout_s
        self.python = python or sys.executable
        # Credential isolation is a property of every child, not of the cases
        # that happen to assert it: the machine's keyring is never in play.
        self.env_extra: dict[str, str] = dict(env_extra or {})

    # ── argv ────────────────────────────────────────────────────────────
    def argv(self, *args: str) -> list[str]:
        return [self.python, "-m", "paperforge", "--vault", str(self.vault), *args]

    def _env(self, extra: dict[str, str] | None) -> dict[str, str]:
        env = {**os.environ, "PAPERFORGE_VAULT": str(self.vault)}
        # The child runs from the repository root (the package is importable
        # there) with the harness on the path so the isolated keyring backend
        # resolves; the vault is addressed by --vault, never by cwd.
        path_parts = [str(REPO_ROOT), str(Path(__file__).resolve().parent)]
        existing = env.get("PYTHONPATH", "")
        if existing:
            path_parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(path_parts)
        env.pop("PADDLEOCR_JOB_URL", None)  # the canonical config decides, not the shell
        env.update(self.env_extra)
        if extra:
            env.update(extra)
        return env

    # ── calls ───────────────────────────────────────────────────────────
    def run(
        self,
        *args: str,
        expect: int | None = 0,
        stdin: str | None = None,
        timeout_s: int | None = None,
        env: dict[str, str] | None = None,
    ) -> CliResult:
        argv = self.argv(*args)
        started = time.time()
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                input=stdin,
                timeout=timeout_s or self.timeout_s,
                env=self._env(env),
                cwd=str(REPO_ROOT),
            )
        except subprocess.TimeoutExpired as exc:
            duration = int((time.time() - started) * 1000)
            self.case.command(argv, returncode=-1, duration_ms=duration, stderr="timeout")
            raise AssertionError(f"command timed out after {timeout_s or self.timeout_s}s: {argv}") from exc
        duration = int((time.time() - started) * 1000)
        result = CliResult(argv, proc.returncode, proc.stdout or "", proc.stderr or "", duration)
        self.case.command(
            argv,
            returncode=result.returncode,
            duration_ms=duration,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        if expect is not None and result.returncode != expect:
            self.case.check(
                f"exit {expect}: {' '.join(args)}",
                False,
                f"rc={result.returncode} stderr={result.tail()}",
            )
        return result

    def json(self, *args: str, expect: int | None = 0, **kwargs: Any) -> CliResult:
        return self.run(*args, "--json", expect=expect, **kwargs)

    def run_stream(
        self,
        *args: str,
        stop_on: Callable[[dict[str, Any]], bool] | None = None,
        stop_after_s: float = 0.0,
        timeout_s: int | None = None,
    ) -> StreamRun:
        """Stream NDJSON; optionally end the run with the cooperative stop token.

        The stop is *observational*: it fires on a real stream event (or a
        deadline), exactly as the plugin's Stop control does, so the case asserts
        the same cancellation contract the UI relies on.
        """
        argv = self.argv(*args)
        started = time.time()
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._env(None),
            cwd=str(REPO_ROOT),
        )
        events: list[dict[str, Any]] = []
        stopped = False
        stop_error = ""
        expired = False
        limit = float(timeout_s or self.timeout_s)
        assert proc.stdout is not None and proc.stdin is not None

        def _on_deadline() -> None:
            # A stream that stops producing output must not burn the job: kill it
            # so the read loop ends and the case reports the timeout honestly.
            nonlocal expired
            expired = True
            proc.kill()

        watchdog = threading.Timer(limit, _on_deadline)
        watchdog.daemon = True
        watchdog.start()

        def _write_stop() -> None:
            nonlocal stopped, stop_error
            if stopped:
                return
            try:
                proc.stdin.write(STOP_TOKEN)
                proc.stdin.flush()
                stopped = True
            except (OSError, ValueError) as exc:
                # Silence here costs a failing case its diagnosis: say why.
                stop_error = f"{type(exc).__name__}: {exc}"

        def _stop_by_deadline() -> None:
            # The stop has to be able to fire when the stream goes quiet: waiting
            # for the next line would let a silent poll loop outlive its budget.
            _write_stop()

        stop_timer: threading.Timer | None = None
        if stop_after_s:
            stop_timer = threading.Timer(float(stop_after_s), _stop_by_deadline)
            stop_timer.daemon = True
            stop_timer.start()
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    parsed = None
                if not isinstance(parsed, dict):
                    # A non-object line is a protocol violation worth seeing, not
                    # crashing on: the case asserts the vocabulary explicitly.
                    parsed = {"event": "unparsed", "raw": line[:300]}
                event: dict[str, Any] = parsed
                events.append(event)
                stop_now = stop_on is not None and stop_on(event)
                if not stopped and (stop_now or (stop_after_s and time.time() - started >= stop_after_s)):
                    _write_stop()
        finally:
            watchdog.cancel()
            if stop_timer is not None:
                stop_timer.cancel()
            try:
                proc.stdin.close()
            except OSError:
                pass
        stderr = ""
        try:
            _, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate()
        # `expired` is a fact of the run, not a verdict: a case whose stop leg is not
        # honoured must be able to record that as its own blocker instead of turning
        # the harness's guard into a red assertion.
        duration = int((time.time() - started) * 1000)
        run = StreamRun(
            argv, events, int(proc.returncode or 0), duration, stopped, expired, stderr or ""
        )
        self.case.command(
            argv,
            returncode=run.returncode,
            duration_ms=duration,
            stdout=json.dumps(events, ensure_ascii=False)[:20000],
            stderr=stderr or "",
        )
        if stop_on is not None or stop_after_s:
            self.case.check(
                "stream stopped cooperatively",
                stopped,
                stop_error or "no stop token was written",
            )
        return run

    # ── convenience ─────────────────────────────────────────────────────
    def action_args(
        self,
        action_id: str,
        keys: tuple[str, ...] = (),
        *,
        confirm: str | None = None,
        follow: str = "none",
    ) -> list[str]:
        """argv for one registry action, exactly as a client dispatches it.

        The plugin never builds these strings: it reads `execution_mode` from the
        action descriptor and calls the same `action run` surface.  Driving it
        here keeps the harness on the contract the clients actually consume.
        """
        args = ["action", "run", action_id, "--json", "--follow", follow]
        if keys:
            args += ["--scope", "papers"]
            for key in keys:
                args += ["--key", key]
        if confirm:
            args += ["--confirm", confirm]
        return args

    def action_stream(
        self,
        action_id: str,
        keys: tuple[str, ...] = (),
        *,
        confirm: str | None = None,
        follow: str = "none",
        **kwargs: Any,
    ) -> StreamRun:
        return self.run_stream(
            *self.action_args(action_id, keys, confirm=confirm, follow=follow), **kwargs
        )

    def probe(self, module: str) -> dict[str, Any]:
        result = self.json("probe", module)
        payload = result.payload or {}
        return payload if module == "all" else payload

    def config_set(self, key: str, value: str) -> CliResult:
        return self.run("config", "set", key, value)

    def config_get(self, key: str) -> str:
        result = self.json("config", "get", key)
        data = result.data
        if isinstance(data, dict):
            field = data.get("field")
            if isinstance(field, dict):
                return str(field.get("value", ""))
            return str(data.get("value", ""))
        return str(data or "")

    def note(self, key: str) -> Path:
        """The canonical note for a paper.

        Sync writes notes under a domain directory; resolving a flat
        `Resources/Literature/<key>.md` is the #230 defect, so the lookup is a
        search, never a guess.
        """
        literature = self.vault / "Resources" / "Literature"
        matches = sorted(literature.rglob(f"{key}.md"))
        if not matches:
            raise AssertionError(f"no canonical note for {key} under {literature}")
        return matches[0]

    def set_note_flag(self, key: str, flag: str, value: bool = True) -> None:
        note = self.note(key)
        text = note.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        assert len(parts) >= 3, f"note without frontmatter: {note}"
        lines = parts[1].splitlines(keepends=True)
        rendered = f"{flag}: {'true' if value else 'false'}\n"
        for index, line in enumerate(lines):
            if line.startswith(f"{flag}:"):
                lines[index] = rendered
                break
        else:
            lines.append(rendered)
        parts[1] = "".join(lines)
        note.write_text("---".join(parts), encoding="utf-8")

    def ocr_meta(self, key: str) -> dict[str, Any]:
        path = self.vault / "System" / "PaperForge" / "ocr" / key / "meta.json"
        if not path.is_file():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
