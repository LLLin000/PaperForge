from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from paperforge.core.errors import ErrorCode


@dataclass
class PFError:
    code: ErrorCode
    message: str
    details: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class PFResult:
    ok: bool
    command: str
    version: str
    data: Any = None
    error: PFError | None = None
    warnings: list[str] = field(default_factory=list)
    next_actions: list[dict] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok

    def to_dict(self) -> dict:
        raw: dict[str, Any] = {
            "ok": self.ok,
            "command": self.command,
            "version": self.version,
        }
        if self.data is not None:
            raw["data"] = self.data
        else:
            raw["data"] = None
        if self.error is not None:
            raw["error"] = {
                "code": self.error.code.value,
                "message": self.error.message,
                "details": self.error.details,
            }
            if self.error.suggestions:
                raw["error"]["suggestions"] = self.error.suggestions
        else:
            raw["error"] = None
        if self.warnings:
            raw["warnings"] = self.warnings
        if self.next_actions:
            raw["next_actions"] = self.next_actions
        return raw

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> PFResult:
        error = None
        if data.get("error") is not None:
            err_data = data["error"]
            error = PFError(
                code=ErrorCode(err_data["code"]),
                message=err_data["message"],
                details=err_data.get("details", {}),
                suggestions=err_data.get("suggestions", []),
            )
        return cls(
            ok=data["ok"],
            command=data["command"],
            version=data["version"],
            data=data.get("data"),
            error=error,
            warnings=data.get("warnings", []),
            next_actions=data.get("next_actions", []),
        )
