"""Generic action runner (#163 / T2, #145 §6–§8).

Pipeline: registry lookup fail-closed → scope validation → preflight →
confirmation gate → handler → single PFResult (+ optional follow-up chain).
The runner performs no retries, never invokes a shell, and never spawns
`paperforge` recursively.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.types import (
    ActionContext,
    ActionIntent,
    ActionRequest,
    ActionScope,
    ActionSpec,
    PapersScope,
    PreflightResult,
)
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

MAX_FOLLOW_UP_DEPTH = 4

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
    """ActionContext from the existing CLI context plumbing (C0 seam)."""
    from paperforge.config import load_vault_config, resolve_paths

    try:
        config = load_vault_config(vault)
        paths = resolve_paths(vault)
    except Exception:  # noqa: BLE001 — fail-closed context
        config = {}
        paths = {}
    return ActionContext(vault=vault, config=config, paths=paths)


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
) -> None:
    if spec.confirmation != "required":
        return
    if confirmed_action_id is None:
        raise ActionError(
            ErrorCode.ACTION_CONFIRMATION_REQUIRED.value,
            f"confirmation required — rerun with --confirm {spec.action_id}",
            exit_code=3,
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
) -> PFResult:
    """The #145 §6 pipeline for one action.  Raises ActionError pre-dispatch;
    handler failures become structured PFResults."""
    spec = _require_registered(request.action_id)
    validate_scope(spec, request.scope)
    preflight = spec.preflight(context, request)
    _require_available(preflight)
    _require_confirmation(spec, confirmed_action_id)
    return spec.handler(context, request)


def canonical_dedupe_key(action_id: str, scope: ActionScope) -> str:
    """One dedupe authority: normalized action_id + scope."""
    if scope.kind == "papers":
        normalized = PapersScope(tuple(sorted(set(scope.keys))))
        payload = {"action_id": action_id, "scope": _scope_payload(normalized)}
    else:
        payload = {"action_id": action_id, "scope": {"kind": "all"}}
    return json.dumps(payload, sort_keys=True)


def hydrate_from_registry(intent: ActionIntent) -> dict[str, Any]:
    """Hydrate an emission-time intent into a wire descriptor (registry
    projection).  Unknown ids fail closed."""
    from paperforge.actions.types import scope_from_dict

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
    }


def run_follow_up_chain(
    root_result: PFResult,
    context: ActionContext,
    *,
    mode: str,
) -> PFResult:
    """§8.2: per-invocation dedupe + depth-bounded follow-up execution.

    `mode` is "none" (default) or "auto".  Only automatic local descendants
    execute; confirmation-required descendants are returned as pending.
    """
    root_next = list(root_result.next_actions)
    if mode == "none" or not root_next:
        return root_result

    executed: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()

    queue: list[tuple[int, dict[str, Any]]] = [
        (1, item) for item in root_next if isinstance(item, dict)
    ]
    while queue:
        depth, raw_intent = queue.pop(0)
        try:
            action_id = str(raw_intent["action_id"])
            from paperforge.actions.types import scope_from_dict

            scope = scope_from_dict(dict(raw_intent["scope"]))
        except (KeyError, TypeError, ValueError):
            skipped.append({"action_id": "unknown", "reason_code": "action.invalid_intent"})
            continue
        key = canonical_dedupe_key(action_id, scope)
        if key in seen:
            skipped.append({"action_id": action_id, "reason_code": "action.duplicate"})
            continue
        seen.add(key)
        if depth > MAX_FOLLOW_UP_DEPTH:
            skipped.append({"action_id": action_id, "reason_code": "action.depth_exceeded"})
            continue

        spec = ACTION_REGISTRY.get(action_id)
        if spec is None:
            skipped.append({"action_id": action_id, "reason_code": "action.unknown"})
            continue
        if not (spec.automatic and spec.cost == "local" and spec.confirmation == "none"):
            pending.append({"action_id": action_id, "scope": _scope_payload(scope)})
            continue

        child_request = ActionRequest(action_id=action_id, scope=scope)
        try:
            child = run_action(child_request, context)
        except ActionError as exc:
            skipped.append({"action_id": action_id, "reason_code": exc.code})
            continue
        executed.append({"action_id": action_id, "ok": child.ok})
        for item in child.next_actions:
            if isinstance(item, dict):
                queue.append((depth + 1, item))

    # The outer result keeps only the actions still pending after the
    # selected mode; the execution report lives under data.follow_up_execution
    # (#145 §8.3).  With --follow none nothing executed, so everything stays.
    root_result.next_actions = [dict(item) for item in pending]
    data = root_result.data
    if data is None:
        data = {}
    if isinstance(data, dict):
        data = dict(data)
        data["follow_up_execution"] = {
            "executed": executed,
            "pending": pending,
            "skipped": skipped,
        }
    root_result.data = data
    return root_result



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
