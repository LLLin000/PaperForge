"""`paperforge action` — registry CLI (#163 / T2, #145 §5–§7).

list / describe / run.  Exit codes: pre-dispatch 2 (invalid request) and
3 (confirmation required); dispatched 0 (completed) / 1 (error) / 130
(cancelled, #137).  Descriptors and the wire never carry command/argv.
"""

from __future__ import annotations

import argparse
import signal
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.runner import (
    ActionError,
    build_context,
    descriptor_for,
    run_action,
    run_follow_up_chain,
)
from paperforge.actions.types import (
    ActionRequest,
    ActionScope,
    AllScope,
    PapersScope,
)
from paperforge.core.result import PFResult

EXIT_INVALID_REQUEST = 2
EXIT_CONFIRMATION_REQUIRED = 3
EXIT_CANCELLED = 130


def _error_result(command: str, code: str, message: str, data: object | None = None) -> PFResult:
    from paperforge.core.errors import ErrorCode
    from paperforge.core.result import PFError

    try:
        code_enum = ErrorCode(code)
    except ValueError:
        code_enum = ErrorCode.INTERNAL_ERROR
    return PFResult(
        ok=False,
        command=command,
        version=PF_VERSION,
        data=data,
        error=PFError(code=code_enum, message=message),
    )


def run_list(args: argparse.Namespace) -> int:
    json_output = bool(getattr(args, "json", False))
    rows = []
    for action_id in sorted(ACTION_REGISTRY):
        spec = ACTION_REGISTRY[action_id]
        rows.append({
            "action_id": spec.action_id,
            "label_code": spec.label_code,
            "scope_kinds": list(spec.scope_kinds),
            "cost": spec.cost,
            "impact": spec.impact,
            "confirmation": spec.confirmation,
            "automatic": spec.automatic,
        })
    if json_output:
        result = PFResult(ok=True, command="action.list", version=PF_VERSION, data={"actions": rows})
        print(result.to_json())
    else:
        for row in rows:
            print(f"{row['action_id']:24s} {row['cost']:14s} {row['impact']:12s} confirm={row['confirmation']} auto={row['automatic']}")
    return 0


def run_describe(args: argparse.Namespace) -> int:
    json_output = bool(getattr(args, "json", False))
    action_id = args.action_id
    spec = ACTION_REGISTRY.get(action_id)
    if spec is None:
        result = _error_result("action.describe", "action.unknown", f"unknown action id: {action_id}")
        message = result.error.message if result.error else f"unknown action id: {action_id}"
        print(result.to_json() if json_output else message, file=sys.stderr if not json_output else sys.stdout)
        return EXIT_INVALID_REQUEST
    context = build_context(args.vault_path)
    request = ActionRequest(action_id=action_id, scope=AllScope())
    preflight = spec.preflight(context, request)
    descriptor = descriptor_for(spec, request, preflight)
    if json_output:
        result = PFResult(ok=True, command="action.describe", version=PF_VERSION, data=descriptor)
        print(result.to_json())
    else:
        print(f"{descriptor['action_id']} — {descriptor['availability']}")
        print(f"  reason: {descriptor['availability_reason']}")
        print(f"  cost: {descriptor['cost']} | impact: {descriptor['impact']} | confirm: {descriptor['confirmation']}")
    return 0


def _parse_scope(args: argparse.Namespace) -> ActionScope:
    kind = getattr(args, "scope", "all")
    if kind == "papers":
        keys = getattr(args, "key", None) or []
        return PapersScope(tuple(keys))
    return AllScope()


def run_dispatch(args: argparse.Namespace) -> int:
    """`action run` — the #145 §6 pipeline with exit-code mapping."""
    json_output = bool(getattr(args, "json", False))
    follow = getattr(args, "follow", "none")
    action_id = args.action_id
    confirmed = getattr(args, "confirm", None)
    context = build_context(args.vault_path)
    request = ActionRequest(action_id=action_id, scope=_parse_scope(args))

    try:
        result = run_action(request, context, confirmed_action_id=confirmed)
        if follow != "none":
            result = run_follow_up_chain(result, context, mode=follow)
    except ActionError as exc:
        result = _error_result("action run", exc.code, str(exc), data=exc.data)
        if json_output:
            print(result.to_json())
        else:
            print(result.error.message if result.error else str(exc), file=sys.stderr)
        return exc.exit_code

    if json_output:
        print(result.to_json())
    else:
        if result.ok:
            print(f"ok: {action_id}")
        else:
            print(f"error: {result.error.message if result.error else 'unknown'}", file=sys.stderr)
    return 0 if result.ok else 1


def _install_sigint_handler() -> None:
    """#137: SIGINT/SIGTERM enters the cooperative cancel path — the dispatch
    reports a cancelled terminal (rc130), never a folded rc1."""

    def _raise_cancel(signum: int, _frame: object) -> None:
        raise KeyboardInterrupt(f"action cancelled by signal {signum}")

    try:
        signal.signal(signal.SIGINT, _raise_cancel)
        signal.signal(signal.SIGTERM, _raise_cancel)
    except (ValueError, OSError):
        pass  # non-main thread / platform without the signal — no handler


def run(args: argparse.Namespace) -> int:
    verb = args.action_verb
    if verb == "list":
        return run_list(args)
    if verb == "describe":
        return run_describe(args)
    if verb == "run":
        _install_sigint_handler()
        try:
            return run_dispatch(args)
        except KeyboardInterrupt as exc:
            # #137: cancelled terminal — never folded into rc1.
            from paperforge.actions.runner import cancelled_result

            result = cancelled_result("action run", str(exc))
            if getattr(args, "json", False):
                print(result.to_json())
            else:
                print("cancelled", file=sys.stderr)
            return EXIT_CANCELLED
    print(f"Error: unsupported action verb '{verb}'", file=sys.stderr)
    return EXIT_INVALID_REQUEST
