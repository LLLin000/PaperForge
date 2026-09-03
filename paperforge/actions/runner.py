"""Generic action runner (#163 / T2, #145 §6).

Pipeline: registry lookup fail-closed → scope validation → preflight →
confirmation gate → handler → single PFResult.

The follow-up chain (--follow auto, dedupe, MAX_FOLLOW_UP_DEPTH, child
execution) is T6 (#167) scope — T2 ships `--follow none` only: the root
handler's next_actions are returned unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.types import (
    ActionContext,
    ActionExecutionHooks,
    ActionIntent,
    ActionRequest,
    ActionScope,
    ActionSpec,
    PreflightResult,
)
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

SCHEMA_VERSION = 1


class ActionError(RuntimeError):
    """Pre-dispatch action failure with a stable code and exit code."""

    code: str
    exit_code: int
    data: Any

    def __init__(self, code: str, message: str, exit_code: int, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.data = data


def build_context(vault: Path) -> ActionContext:
    """ActionContext from ONE config snapshot (C0 seam): both the config
    values and the resolved paths derive from the same snapshot, so the
    context is a frozen invocation view."""
    from paperforge.config import load_config, resolve_paths

    try:
        snapshot = load_config(vault)
        values: dict[str, object] = {
            key: cv.value for key, cv in snapshot.values.items()
        }
        paths = resolve_paths(vault, snapshot)
    except Exception:  # noqa: BLE001 — fail-closed context
        values = {}
        paths = {}
    return ActionContext(vault=vault, config=values, paths=paths)


def descriptor_for(
    spec: ActionSpec,
    request: ActionRequest,
    preflight: PreflightResult,
) -> dict[str, Any]:
    """Current action descriptor for the wire — never carries command/argv."""
    return {
        "schema_version": SCHEMA_VERSION,
        "action_id": spec.action_id,
        "label_code": spec.label_code,
        "description_code": spec.description_code,
        "scope": _scope_payload(request.scope),
        "availability": preflight.availability,
        "availability_reason_code": preflight.availability_reason_code,
        "availability_reason": preflight.availability_reason,
        "cost": spec.cost,
        "impact": spec.impact,
        "confirmation": spec.confirmation,
        "automatic": spec.automatic,
        "interruptible": spec.interruptible,
        "execution_mode": spec.execution_mode,
        "preservation_facts": list(preflight.preservation_facts),
        "replacement_facts": list(preflight.replacement_facts),
    }


def _scope_payload(scope: ActionScope) -> dict[str, Any]:
    if scope.kind == "papers":
        return {"kind": "papers", "keys": list(scope.keys)}
    return {"kind": "all"}


def validate_scope(spec: ActionSpec, scope: ActionScope) -> None:
    if scope.kind not in spec.scope_kinds:
        raise ActionError(
            ErrorCode.ACTION_SCOPE_INVALID.value,
            f"action {spec.action_id} does not accept scope kind {scope.kind!r}",
            exit_code=2,
        )
    if scope.kind == "papers" and not scope.keys:
        raise ActionError(
            ErrorCode.ACTION_SCOPE_INVALID.value,
            f"papers scope requires at least one key for {spec.action_id}",
            exit_code=2,
        )


def _require_registered(action_id: str) -> ActionSpec:
    spec = ACTION_REGISTRY.get(action_id)
    if spec is None:
        raise ActionError(
            ErrorCode.ACTION_UNKNOWN.value,
            f"unknown action id: {action_id}",
            exit_code=2,
        )
    return spec


def _require_available(preflight: PreflightResult) -> None:
    if preflight.availability == "unavailable":
        raise ActionError(
            ErrorCode.ACTION_UNAVAILABLE.value,
            preflight.availability_reason,
            exit_code=1,
            data={"availability_reason_code": preflight.availability_reason_code},
        )
    if preflight.availability == "busy":
        raise ActionError(
            ErrorCode.ACTION_BUSY.value,
            preflight.availability_reason,
            exit_code=1,
            data={"availability_reason_code": preflight.availability_reason_code},
        )


def _require_confirmation(
    spec: ActionSpec,
    confirmed_action_id: str | None,
    *,
    descriptor: dict[str, Any],
) -> None:
    if spec.confirmation != "required":
        return
    if confirmed_action_id is None:
        # #163: exit 3 carries the CURRENT action descriptor — the caller
        # renders availability + preservation/replacement facts, then
        # re-runs with --confirm.
        raise ActionError(
            ErrorCode.ACTION_CONFIRMATION_REQUIRED.value,
            f"confirmation required — rerun with --confirm {spec.action_id}",
            exit_code=3,
            data=descriptor,
        )
    if confirmed_action_id != spec.action_id:
        raise ActionError(
            ErrorCode.ACTION_INVALID_REQUEST.value,
            f"--confirm names {confirmed_action_id!r}, not {spec.action_id!r}",
            exit_code=2,
        )


def run_action(
    request: ActionRequest,
    context: ActionContext,
    *,
    confirmed_action_id: str | None = None,
    execution_hooks: ActionExecutionHooks | None = None,
) -> PFResult:
    """The #145 §6 pipeline for one action.

    Raises ActionError pre-dispatch.  Handler failures are converted to
    structured PFResult errors at the runner boundary — a dispatched action
    always produces exactly one PFResult (rc 0/1/130), never a traceback.
    """
    spec = _require_registered(request.action_id)
    validate_scope(spec, request.scope)
    preflight = spec.preflight(context, request)
    _require_available(preflight)
    descriptor = descriptor_for(spec, request, preflight)
    _require_confirmation(spec, confirmed_action_id, descriptor=descriptor)
    handler_context = (
        replace(context, execution_hooks=execution_hooks)
        if execution_hooks is not None
        else context
    )
    try:
        result = spec.handler(handler_context, request)
    except KeyboardInterrupt:
        # #137: the cancellation path owns this — re-raise for rc130.
        raise
    except Exception as exc:  # noqa: BLE001 — structured error boundary
        from paperforge import __version__ as PF_VERSION

        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
    return _validate_handler_result(result, spec.action_id)


def _validate_handler_result(result: Any, action_id: str) -> PFResult:
    """#145 Rev3 guard: handlers MUST return PFResult with data mapping/None."""
    from paperforge import __version__ as PF_VERSION

    if not isinstance(result, PFResult):
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"handler for {action_id} returned {type(result).__name__}, not PFResult",
            ),
        )
    if result.data is not None and not isinstance(result.data, Mapping):
        return PFResult(
            ok=False,
            command="action run",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"handler for {action_id} returned non-mapping data: {type(result.data).__name__}",
            ),
        )
    return result


def hydrate_from_registry(intent: ActionIntent) -> dict[str, Any]:
    """Hydrate an emission-time intent into a wire descriptor (registry
    projection).  Unknown ids fail closed."""
    spec = _require_registered(intent.action_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "action_id": spec.action_id,
        "label_code": spec.label_code,
        "description_code": spec.description_code,
        "scope": _scope_payload(intent.scope),
        "automatic": spec.automatic,
        "cost": spec.cost,
        "impact": spec.impact,
        "confirmation": spec.confirmation,
        "reason": intent.trigger_reason,
        "execution_mode": spec.execution_mode,
    }


def cancelled_result(command: str, message: str) -> PFResult:
    """#137: a cancelled dispatch is a terminal outcome with rc130, never a
    folded rc1.  The PFResult itself stays ok=false with action.cancelled."""
    from paperforge import __version__ as PF_VERSION

    return PFResult(
        ok=False,
        command=command,
        version=PF_VERSION,
        error=PFError(code=ErrorCode.ACTION_CANCELLED, message=message),
    )
