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
from typing import Any, NamedTuple

import pytest

from .evidence import REPO_ROOT, CaseEvidence, evidence_root, write_index
from .recorder import CliHost
from .stub import OcrStub
from .stub_embed import EmbedStub


def force_rmtree(root: Path) -> None:
    """Windows-safe removal: clear the read-only bit before unlinking."""
    for dirpath, dirnames, filenames in os.walk(str(root)):
        for name in [*filenames, *dirnames]:
            try:
                os.chmod(os.path.join(dirpath, name), stat.S_IWRITE)
            except OSError:
                pass
    shutil.rmtree(str(root), ignore_errors=True)


def harness_keyring_env(vault: Path) -> dict[str, str]:
    """A credential store the machine's keyring never sees.

    The backend module lives beside this file and keeps its secrets in a JSON
    file *outside* the vault - inside it, a case could not tell "the secret
    reach the keyring" apart from "the secret landed in the vault".
    """
    return {
        "PAPERFORGE_KEYRING_BACKEND": "harness_keyring.Keyring",
        "PAPERFORGE_HARNESS_KEYRING_FILE": str(vault.parent / f"{vault.name}-keyring.json"),
    }


def _keyring_store(vault: Path) -> Path:
    return vault.parent / f"{vault.name}-keyring.json"


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
    store = _keyring_store(built)
    if store.exists():
        store.unlink()


@pytest.fixture
def cli(vault: Path, case: CaseEvidence) -> CliHost:
    return CliHost(vault, case, env_extra=harness_keyring_env(vault))


@pytest.fixture
def render_vault(case: CaseEvidence) -> Iterator[Path]:
    """The repo's own render fixture vault (TSTONE001 with a completed OCR run).

    Built by the plugin's e2e builder so the harness and the H matrix share one
    fixture definition: the R candidate (figure_a1) and the P proposal
    (figure_2) come out of real reconciliation, not a hand-written stub, and the
    canonical PDF the materializer crops is present.
    """
    import importlib.util
    import tempfile

    builder = REPO_ROOT / "paperforge" / "plugin" / "test" / "fixtures" / "build_e2e_vault.py"
    spec = importlib.util.spec_from_file_location("pf_build_e2e_vault", builder)
    assert spec is not None and spec.loader is not None
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    base = Path(tempfile.mkdtemp(prefix="pf_harness_render_"))
    module.VAULT = base / "vault"
    module.EMPTY_VAULT = base / "empty"
    module.build()
    yield module.VAULT
    if base.exists():
        force_rmtree(base)


@pytest.fixture
def render_cli(render_vault: Path, case: CaseEvidence) -> CliHost:
    """A CLI host bound to the render fixture vault (not the standard one)."""
    return CliHost(render_vault, case, env_extra=harness_keyring_env(render_vault))


@pytest.fixture
def ocr_cli(cli: CliHost, case: CaseEvidence) -> CliHost:
    """A CLI host whose vault holds an OCR credential in ITS OWN keyring.

    The provider cases used to pass on whatever credential the machine running
    the suite happened to have installed (auth status reported `keyring`, and the
    vault's legacy .env token is not the authority).  Isolation is asserted here,
    not assumed: the token is written through the product's own command into this
    case's keyring file.
    """
    seeded = cli.json(
        "auth", "set", "ocr", "--stdin", "--replace", stdin="pf-harness-ocr-token\n"
    )
    case.check(
        "the OCR credential is seeded in the isolated keyring",
        seeded.returncode == 0,
        seeded.tail(),
    )
    return cli


@pytest.fixture
def render_ocr_cli(render_cli: CliHost, case: CaseEvidence) -> CliHost:
    """A credentialed CLI host for the render fixture vault (OCR cases)."""
    seeded = render_cli.json(
        "auth", "set", "ocr", "--stdin", "--replace", stdin="pf-harness-ocr-token\n"
    )
    case.check(
        "the OCR credential is seeded in the isolated keyring",
        seeded.returncode == 0,
        seeded.tail(),
    )
    return render_cli


class RetrievalSetup(NamedTuple):
    """A CLI host whose vault is wired to a controlled embedding provider."""

    cli: CliHost
    stub: EmbedStub


@pytest.fixture
def embed_stub(case: CaseEvidence) -> Iterator[Callable[..., EmbedStub]]:
    """Factory for loopback embedding providers; every one is stopped at teardown."""
    started: list[EmbedStub] = []

    def _start(**kwargs: Any) -> EmbedStub:
        stub = EmbedStub(**kwargs)
        stub.start()
        started.append(stub)
        return stub

    yield _start
    for stub in started:
        stub.stop()


@pytest.fixture
def retrieval(render_cli: CliHost, case: CaseEvidence, embed_stub: Callable[..., EmbedStub]) -> RetrievalSetup:
    """The render vault with an embedding credential and a controlled provider.

    The credential goes into this case's isolated keyring through the product's
    own command, and the provider endpoint/model go into canonical config - the
    same two seams the plugin's settings write.
    """
    seeded = render_cli.json(
        "auth", "set", "embedding", "--stdin", "--replace", stdin="pf-harness-embed-token\n"
    )
    case.check(
        "the embedding credential is seeded in the isolated keyring",
        seeded.returncode == 0,
        seeded.tail(),
    )
    stub = embed_stub(mode="success")
    base = render_cli.json("config", "set", "vector_db_api_base", stub.base_url)
    model = render_cli.json("config", "set", "vector_db_api_model", "stub-embedding")
    case.check("the provider endpoint is canonical config", base.returncode == 0, base.tail())
    case.check("the provider model is canonical config", model.returncode == 0, model.tail())
    return RetrievalSetup(render_cli, stub)


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
