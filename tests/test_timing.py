"""Phase timing contract (diagnostics for "sync is sometimes very slow").

stdout is the machine protocol; timing must never touch it. Emission policy:
unset env → only phases >= SLOW_MS; PAPERFORGE_TIMING=1 → all; =0 → none.
"""

from __future__ import annotations

import time

from paperforge.core import timing


def test_phase_records_and_summary() -> None:
    timing.reset()
    with timing.phase("a"):
        time.sleep(0.002)
    with timing.phase("b"):
        pass
    summary = timing.summary()
    assert set(summary) == {"a", "b"}
    assert summary["a"] >= 1.0
    assert timing.total_ms() >= summary["a"]


def test_slow_only_by_default_and_silent_on_zero(monkeypatch, capsys) -> None:
    monkeypatch.delenv("PAPERFORGE_TIMING", raising=False)
    timing.reset()
    with timing.phase("fast"):
        pass
    assert capsys.readouterr().err == ""
    # a phase over the threshold is always reported
    monkeypatch.setattr(timing, "SLOW_MS", 0.0)
    with timing.phase("slow"):
        pass
    err = capsys.readouterr().err
    assert "[PF:time] slow" in err
    monkeypatch.setattr(timing, "SLOW_MS", 1000.0)

    monkeypatch.setenv("PAPERFORGE_TIMING", "0")
    timing.reset()
    with timing.phase("muted"):
        pass
    assert capsys.readouterr().err == ""


def test_verbose_reports_every_phase_and_total(monkeypatch, capsys) -> None:
    monkeypatch.setenv("PAPERFORGE_TIMING", "1")
    timing.reset()
    timing.set_command("sync")
    with timing.phase("sync.service"):
        pass
    timing.emit_total()
    err = capsys.readouterr().err
    assert "[PF:time] sync.service" in err
    assert "[PF:time] command=sync total=" in err
    assert timing.summary()["sync.service"] >= 0.0


def test_timing_never_writes_stdout(monkeypatch, capsys) -> None:
    monkeypatch.setenv("PAPERFORGE_TIMING", "1")
    timing.reset()
    timing.set_command("sync")
    with timing.phase("p"):
        pass
    timing.emit_total()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err != ""
