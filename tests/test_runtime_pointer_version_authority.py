"""#267 regression: pointer version authority = the environment's distribution.

On 2026-10-04 the owner machine carried a pointer claiming `2.0.0rc5` while the
interpreter's installed distribution was `2.0.0rc1`, because `publish_pointer`
took `paperforge_version` from the imported source (`paperforge.__version__`),
which a checkout on the cwd can shadow. The fix reads the distribution metadata
of the running environment first; the source constant remains a fallback for
trees with no installed distribution.

The subprocess test reproduces the exact mechanism: a fake `paperforge` package
(declaring 9.9.9) sits on the cwd, its `runtime_pointer.py` is the real one, and
the published payload must still record the environment's distribution version —
never the shadowing source's.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pytest

from paperforge import runtime_pointer


def _dist_version_or_none() -> str | None:
    try:
        return version("paperforge")
    except PackageNotFoundError:
        return None


def test_publish_pointer_uses_distribution_over_source(monkeypatch, tmp_path):
    """Monkeypatched source version must not win while a dist is installed."""
    dist = _dist_version_or_none()
    if dist is None:
        pytest.skip("no installed paperforge distribution in this environment")

    monkeypatch.setattr("paperforge.__version__", "9.9.9-shadow", raising=True)
    published = runtime_pointer.publish_pointer(home=tmp_path)
    payload = json.loads(published.read_text(encoding="utf-8"))
    assert payload["paperforge_version"] == dist
    assert payload["paperforge_version"] != "9.9.9-shadow"


def test_publish_pointer_cwd_shadow_cannot_forge_the_claim(tmp_path):
    """The owner-machine mechanism, end to end in a subprocess.

    A fake package on the cwd shadows the real one for imports; because the
    fake `runtime_pointer.py` is the real module, the payload proves which
    version source the publisher consulted.
    """
    dist = _dist_version_or_none()
    if dist is None:
        pytest.skip("no installed paperforge distribution in this environment")

    fake_pkg = tmp_path / "shadow" / "paperforge"
    fake_pkg.mkdir(parents=True)
    (fake_pkg / "__init__.py").write_text(
        '__version__ = "9.9.9-shadow"\n', encoding="utf-8"
    )
    shutil.copy2(Path(runtime_pointer.__file__), fake_pkg / "runtime_pointer.py")

    home = tmp_path / "home"
    script = (
        "import json, sys;"
        "from paperforge.runtime_pointer import publish_pointer;"
        f"p = publish_pointer(home=__import__('pathlib').Path(r'{home}'));"
        "print(p.read_text(encoding='utf-8'))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(fake_pkg.parent),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["paperforge_version"] == dist
    assert payload["paperforge_version"] != "9.9.9-shadow"
