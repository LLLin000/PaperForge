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


@dataclass
class PFResult:
    ok: bool
    command: str
    version: str
    data: Any = None
    error: PFError | None = None

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
        else:
            raw["error"] = None
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
            )
        return cls(
            ok=data["ok"],
            command=data["command"],
            version=data["version"],
            data=data.get("data"),
            error=error,
        )
