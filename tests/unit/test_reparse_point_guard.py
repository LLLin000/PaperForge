"""The reparse-point guard must not read a missing path as a junction.

Regression (found by the CLI-host acceptance case F03): with ctypes' default
restype, GetFileAttributesW returns INVALID_FILE_ATTRIBUTES as -1, so
``attrs & FILE_ATTRIBUTE_REPARSE_POINT`` was truthy for every path that does not
exist.  ``accept_proposal`` checks that mask on its write destinations and on
``.paperforge-r-promotion.lock`` before doing anything, so on Windows it refused
every acceptance with ACCEPT_PROPOSAL_PATH_UNSAFE - and "destination does not
exist yet" is the precondition for accepting a NEW canonical object.

This lives in tests/unit/ on purpose: the Windows branch is only reachable on
Windows, and the root-level test files run on ubuntu in CI, which is how the
defect stayed green.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from paperforge.promote_r import _is_reparse_point, _raw_path_has_symlink


def _can_create_junction() -> bool:
    if os.name != "nt":
        return False
    try:
        base = Path(os.environ.get("TEMP", ".")) / "_reparse_guard_probe"
        target = base / "target"
        link = base / "link"
        target.mkdir(parents=True, exist_ok=True)
        if link.exists():
            link.rmdir()
        subprocess.run(
            [
                "powershell",
                "-Command",
                f"New-Item -ItemType Junction -Path '{link}' -Target '{target}'",
            ],
            check=True,
            capture_output=True,
        )
        ok = link.is_dir()
        for path in (link, target, base):
            try:
                path.rmdir()
            except OSError:
                pass
        return ok
    except Exception:  # noqa: BLE001 - probe only
        return False


JUNCTION_AVAILABLE = _can_create_junction()


def test_a_missing_path_is_not_a_reparse_point(tmp_path: Path) -> None:
    assert _is_reparse_point(tmp_path / "not-here") is False
    assert _is_reparse_point(tmp_path / "not-here" / "deeper.txt") is False


def test_an_ordinary_file_is_not_a_reparse_point(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    assert _is_reparse_point(target) is False


def test_accept_proposal_destinations_may_not_exist_yet(tmp_path: Path) -> None:
    """The exact precondition the acceptance guard has to pass.

    A new proposal's canonical destinations do not exist before acceptance, and
    the promotion lock is normally absent too; neither may be read as a
    symlinked/redirected surface.
    """
    root = tmp_path / "TSTONE001"
    (root / "structure").mkdir(parents=True)
    (root / "structure" / "figure_inventory.json").write_text("{}", encoding="utf-8")
    for relative in (
        ".paperforge-r-promotion.lock",
        "assets/figures/figure_002.jpg",
        "render/figures/figure_002.md",
        "render/reconciliation.proposals.json",
    ):
        assert _raw_path_has_symlink(root, relative) is False, relative


@pytest.mark.skipif(not JUNCTION_AVAILABLE, reason="junction creation unavailable")
def test_a_real_junction_is_still_rejected(tmp_path: Path) -> None:
    """The guard has to keep the property it exists for."""
    target = tmp_path / "outside"
    target.mkdir()
    link = tmp_path / "root" / "link"
    link.parent.mkdir()
    created = subprocess.run(
        [
            "powershell",
            "-Command",
            f"New-Item -ItemType Junction -Path '{link}' -Target '{target}'",
        ],
        capture_output=True,
    )
    assert created.returncode == 0, created.stderr
    assert _is_reparse_point(link) is True
    assert _raw_path_has_symlink(tmp_path / "root", "link/secret.txt") is True
