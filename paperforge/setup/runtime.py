"""Read-only check of dependencies owned by the independent runtime installer."""

from __future__ import annotations

import importlib.util

from paperforge.core.errors import ErrorCode
from paperforge.setup import SetupStepResult

VECTOR_CAPABILITY_IMPORTS = ("openai", "chromadb", "sqlite_vec")


def vector_extras_missing() -> list[str]:
    return [
        module
        for module in VECTOR_CAPABILITY_IMPORTS
        if importlib.util.find_spec(module) is None
    ]


def vector_extras_present() -> bool:
    return not vector_extras_missing()


def check_runtime_dependencies() -> SetupStepResult:
    """Report missing extras; only ``paperforge runtime install`` may install them."""
    missing = vector_extras_missing()
    if missing:
        return SetupStepResult(
            step="runtime_dependencies",
            ok=False,
            message=(
                "Runtime dependencies are missing: " + ", ".join(missing)
                + ". Run `paperforge runtime repair` outside Obsidian."
            ),
            error=ErrorCode.VALIDATION_ERROR.value,
            details={"missing": missing},
        )
    return SetupStepResult(
        step="runtime_dependencies",
        ok=True,
        message="Runtime dependencies are available",
    )
