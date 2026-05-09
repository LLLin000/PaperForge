"""PaperForge setup package — modular setup components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SetupStepResult:
    """Result of a single setup step."""

    step: str
    ok: bool = True
    message: str = ""
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "ok": self.ok,
            "message": self.message,
            "error": self.error,
        }
