"""Fixtures for the CLI-host acceptance cases.

Two rules hold for everything here:

* the vault is disposable and is *asserted* to be disposable before a case runs
  (the 2026-08-14 prune incident started with a path helper that silently meant
  the vault root);
* the evidence record is written even when a case fails, so a red run ships the
  commands, exit codes and digests that produced it.
"""

from __future__ import annotations

import os
import shutil
import stat
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from .evidence import CaseEvidence, evidence_root, write_index
from .recorder import CliHost
from .stub import OcrStub


def force_rmtree(root: Path) -> None:
    """Windows-safe removal: clear the read-only bit before unlinking."""
    for dirpath, dirnames, filenames in os.walk(str(root)):
        for name in [*filenames, *dirnames]:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(str(root), ignore_errors=True)


@pytest.fixture
def case(request: pytest.FixtureRequest) -> Iterator[CaseEvidence]:
    """The case's evidence record; module-level CASE_ID/TITLE/HOST_SPEC_CASE drive it."""
    module = request.module
    record = CaseEvidence(
        getattr(module, "CASE_ID", request.node.name),
        getattr(module, "TITLE", request.node.name),
        host_spec_case=getattr(module, "HOST_SPEC_CASE", ""),
    )
    yield record
    record.write()
    # A recorded failure must ALSO fail the test: an evidence-only failure would
    # let a red case report green (the gate-that-cannot-fail class, #224).
    if record.failure:
        pytest.fail(f"{record.case_id}: {record.failure}", pytrace=False)


@pytest.fixture
def vault(case: CaseEvidence) -> Iterator[Path]:
    """A disposable 'standard' vault: config, dirs, exports, per-paper PDFs."""
    from fixtures.vault_builder import VaultBuilder

    built = Path(VaultBuilder().build("standard"))
    if not any(marker in str(built).lower() for marker in ("tmp", "temp")):
        raise AssertionError(f"isolation violation: {built} is not a disposable path")
    yield built
    if built.exists():
        force_rmtree(built)


@pytest.fixture
def cli(vault: Path, case: CaseEvidence) -> CliHost:
    return CliHost(vault, case)


@pytest.fixture
def ocr_stub(case: CaseEvidence) -> Iterator[Callable[..., OcrStub]]:
    """Factory for loopback OCR providers; every one is stopped at teardown."""
    started: list[OcrStub] = []

    def _start(**kwargs: Any) -> OcrStub:
        stub = OcrStub(**kwargs)
        stub.start()
        started.append(stub)
        return stub

    yield _start
    for stub in started:
        stub.stop()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write the run index a per-area report cites in place of a hand-kept table."""
    root = evidence_root()
    records = [path for path in sorted(root.glob("*.json")) if path.stem != "index"]
    if records:
        write_index(records, root)
