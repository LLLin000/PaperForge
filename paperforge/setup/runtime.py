"""Runtime dependency extras (#174 / #143 python-first journey).

The runtime package itself is installed EXACTLY once by the bootstrap
(plugin venv + ONE pinned install, or `pip install paperforge`).
`paperforge setup` after cutover only ENSURES the [vector] extras the core
features require are importable in the CURRENT runtime:

- already present  → no-op (plugin-first pinned `paperforge[vector]`
  install satisfies this; the dependency step must not reinstall anything)
- missing          → install `paperforge[vector]==<running version>` into
  the CURRENT interpreter, then fresh-child verify

Never reinstalls the package, never touches credentials (C1 boundary),
and the pointer is published only after this step passes.
"""

from __future__ import annotations

import subprocess
import sys

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.setup import SetupStepResult

# The vector extras are the runtime requirements for embed build/retrieve
# (#119: a bare install looks healthy but crashes on the first Build Index
# click).
VECTOR_CAPABILITY_IMPORTS = ("openai", "chromadb", "sqlite_vec")
VECTOR_RUNTIME_PROBE = (
    "import paperforge, openai, chromadb, sqlite_vec;"
    "from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider;"
    " print(paperforge.__version__)"
)


def vector_extras_present() -> bool:
    """True only when every vector capability actually imports.

    ``find_spec`` verifies that a module name is discoverable, not that the
    installed package is internally complete. Importing catches interrupted
    upgrades and missing files before the pointer is published.
    """
    for module in VECTOR_CAPABILITY_IMPORTS:
        try:
            __import__(module)
        except Exception:
            return False
    return True


def verify_runtime_in_child(python_path: str | None = None) -> tuple[bool, str]:
    """Verify the complete vector runtime in a fresh interpreter."""
    executable = python_path or sys.executable
    try:
        result = subprocess.run(
            [str(executable), "-I", "-c", VECTOR_RUNTIME_PROBE],
            capture_output=True,
            text=True,
            timeout=60,
        )
        version = result.stdout.strip()
        return result.returncode == 0 and bool(version), version
    except Exception:
        return False, ""


def _fresh_child_verify() -> tuple[bool, str]:
    """Fresh interpreter verification for the current runtime."""
    return verify_runtime_in_child()


def ensure_runtime_dependencies() -> SetupStepResult:
    """Ensure vector extras in the CURRENT runtime; no-op when present.

    Returns a SetupStepResult; the pointer MUST NOT be published unless
    this step is ok."""
    if vector_extras_present():
        return SetupStepResult(
            step="runtime_dependencies",
            ok=True,
            message="Vector extras already present (no-op)",
        )

    spec = f"paperforge[vector]=={__version__}"
    try:
        pip = subprocess.run(
            [sys.executable, "-m", "pip", "install", spec],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as exc:  # noqa: BLE001 — structured error boundary
        return SetupStepResult(
            step="runtime_dependencies",
            ok=False,
            message=f"pip install failed: {exc}",
            error=ErrorCode.INTERNAL_ERROR,
        )
    if pip.returncode != 0:
        return SetupStepResult(
            step="runtime_dependencies",
            ok=False,
            message=f"pip install failed: {pip.stderr[:300]}",
            error=ErrorCode.INTERNAL_ERROR,
        )

    verified, observed = _fresh_child_verify()
    if not verified or observed != __version__:
        return SetupStepResult(
            step="runtime_dependencies",
            ok=False,
            message=(
                f"fresh-child verify failed after extras install "
                f"(observed {observed!r} != running {__version__!r})"
            ),
            error=ErrorCode.INTERNAL_ERROR,
        )
    return SetupStepResult(
        step="runtime_dependencies",
        ok=True,
        message=f"Installed {spec}; verified in fresh interpreter",
    )
