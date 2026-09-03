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
)
from paperforge.actions.types import (
    ActionExecutionHooks,
    ActionRequest,
    ActionScope,
    AllScope,
    PapersScope,
)
from paperforge.core.errors import ErrorCode
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
            "execution_mode": spec.execution_mode,
        })
    if json_output:
        result = PFResult(ok=True, command="action.list", version=PF_VERSION, data={"actions": rows})
        print(result.to_json())
    else:
        for row in rows:
            print(
                f"{row['action_id']:24s} {row['cost']:14s} "
                f"{row['impact']:12s} confirm={row['confirmation']} "
                f"auto={row['automatic']}"
            )
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
        keys_file = getattr(args, "keys_file", None)
        if keys_file:
            try:
                from pathlib import Path

                keys.append(Path(keys_file).read_text(encoding="utf-8-sig"))
            except Exception as exc:  # noqa: BLE001 — surface a clear error
                print(f"Error: cannot read keys file {keys_file}: {exc}", file=sys.stderr)
                return PapersScope(tuple())
        from paperforge.core.keys import normalize_paper_keys

        return PapersScope(tuple(normalize_paper_keys(keys)))
    return AllScope()


def run_preflight(args: argparse.Namespace) -> int:
    """M2-C (Control Plane Closure): `action preflight` — observe whether an
    action CAN run (availability) and SHOULD run per paper (applicability),
    WITHOUT executing anything.  Read-only: no meta mutation, no provider
    calls, no build."""
    import json as _json

    from paperforge.actions.registry import ACTION_REGISTRY
    from paperforge.actions.runner import build_context, validate_scope
    from paperforge.actions.types import ActionRequest, scope_to_dict

    context = build_context(args.vault_path)
    spec = ACTION_REGISTRY.get(args.action_id)
    if spec is None:
        print(f"Error: unknown action {args.action_id}", file=sys.stderr)
        return 2
    scope = _parse_scope(args)
    try:
        validate_scope(spec, scope)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    result = spec.preflight(context, ActionRequest(action_id=args.action_id, scope=scope))

    if getattr(args, "json", False):
        payload = {
            "schema_version": 1,
            "action_id": args.action_id,
            "scope": scope_to_dict(scope),
            "availability": result.availability,
            "availability_reason_code": result.availability_reason_code,
            "availability_reason": result.availability_reason,
            "summary": result.summary(),
            "per_key": {
                p.key: {
                    "applicability": p.applicability,
                    "reason_code": p.reason_code,
                    "reason": p.reason,
                    "recommended_action_id": p.recommended_action_id,
                }
                for p in result.per_key
            },
        }
        print(_json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"Action: {args.action_id}")
    print(f"Availability: {result.availability} ({result.availability_reason_code})")
    print(f"  {result.availability_reason}")
    if result.per_key:
        print()
        print(f"{'Paper':12s} {'Applicability':16s} Reason")
        print("-" * 60)
        for p in result.per_key:
            rec = f" → {p.recommended_action_id}" if p.recommended_action_id else ""
            print(f"{p.key:12s} {p.applicability:16s} {p.reason}{rec}")
        s = result.summary()
        print(
            f"\nNeeded {s['needed']} | No-op {s['noop']} | Blocked {s['blocked']} | "
            f"N/A {s['not_applicable']}"
        )
    return 0


def run_dispatch(args: argparse.Namespace) -> int:
    """`action run` — the #145 §6 pipeline with exit-code mapping.

    The explicit CLI root ALWAYS runs the T2 pipeline (preflight →
    confirmation gate → handler): missing confirm → rc3 + descriptor,
    wrong confirm → rc2, invalid preflight → rc1.  `--follow auto` takes
    over DESCENDANTS only (#167 P0-1): after a successful root, reconcile
    derives the next layer and the generic chain runner executes
    automatic-local children inline, pends the rest."""
    json_output = bool(getattr(args, "json", False))
    action_id = args.action_id
    confirmed = getattr(args, "confirm", None)
    follow = getattr(args, "follow", "none")
    context = build_context(args.vault_path)
    request = ActionRequest(action_id=action_id, scope=_parse_scope(args))

    spec = ACTION_REGISTRY.get(action_id)
    is_stream = json_output and (spec is not None and spec.execution_mode == "stream")

    execution_hooks = None
    if is_stream:
        from paperforge.core.cancellation import make_cancellation_token
        from paperforge.core.ndjson import (
            emit_item_result,
            emit_phase,
            emit_progress,
            emit_start,
            emit_terminal,
        )

        total = len(request.scope.keys) if request.scope.kind == "papers" else None
        emit_start(action_id, total=total, scope=request.scope.kind)
        _is_stopped, restore = make_cancellation_token()
        execution_hooks = ActionExecutionHooks(
            is_stopped=_is_stopped,
            phase=lambda phase: emit_phase(action_id, phase),
            progress=lambda current, progress_total, item_id: emit_progress(
                action_id, current, progress_total, item_id
            ),
            item_result=lambda item_id, status: emit_item_result(
                action_id, item_id, status
            ),
        )
    else:
        def restore() -> None:
            return None

    try:
        result = run_action(
            request,
            context,
            confirmed_action_id=confirmed,
            execution_hooks=execution_hooks,
        )
    except ActionError as exc:
        result = _error_result("action run", exc.code, str(exc), data=exc.data)
        if json_output:
            if is_stream:
                emit_terminal("error", action_id, result)
            else:
                print(result.to_json())
        else:
            print(result.error.message if result.error else str(exc), file=sys.stderr)
        restore()
        return exc.exit_code
    except KeyboardInterrupt as exc:
        from paperforge.actions.runner import cancelled_result

        result = cancelled_result("action run", str(exc))
        if json_output:
            if is_stream:
                emit_terminal("cancelled", action_id, result)
            else:
                print(result.to_json())
        else:
            print("cancelled", file=sys.stderr)
        restore()
        return EXIT_CANCELLED

    restore()
    if result.error is not None and result.error.code == ErrorCode.ACTION_CANCELLED:
        if json_output:
            if is_stream:
                emit_terminal("cancelled", action_id, result)
            else:
                print(result.to_json())
        else:
            print("cancelled", file=sys.stderr)
        return EXIT_CANCELLED


    if result.ok and follow == "auto":
        _run_descendants(args, request, context, result)

    if json_output:
        if is_stream:
            emit_terminal("result" if result.ok else "error", action_id, result)
        else:
            print(result.to_json())
    else:
        if result.ok:
            print(f"ok: {action_id}")
        else:
            print(f"error: {result.error.message if result.error else 'unknown'}", file=sys.stderr)
    return 0 if result.ok else 1

def _run_descendants(args: argparse.Namespace, request: ActionRequest, context, root_result) -> None:
    """#167 P0-1: follow auto governs descendants only — after a successful
    explicit root, reconcile(successful scope) derives the next layer and
    the generic chain runner executes it (children start at depth 1)."""
    from paperforge.actions.chain import run_chain
    from paperforge.reconcile import reconcile

    keys = list(request.scope.keys) if request.scope.kind == "papers" else None
    try:
        children = reconcile(args.vault_path, keys)
    except Exception:  # noqa: BLE001 — a broken producer never fails the root
        return
    chain = run_chain(list(children.next_actions or []), context, root_depth=1)
    wire = chain.to_wire()
    data = dict(root_result.data or {})
    data["chain"] = wire
    root_result.data = data
    root_result.next_actions = chain.pending
    if not chain.ok:
        root_result.ok = False
        from paperforge.core.errors import ErrorCode
        from paperforge.core.result import PFError

        failed = next((s for s in chain.steps if s.status == "failed"), None)
        root_result.error = PFError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"follow-up action failed: {failed.action_id}" if failed else "follow-up chain failed",
        )


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
            spec = ACTION_REGISTRY.get(getattr(args, "action_id", ""))
            if getattr(args, "json", False):
                if spec is not None and spec.execution_mode == "stream":
                    from paperforge.core.ndjson import emit_terminal

                    emit_terminal("cancelled", spec.action_id, result)
                else:
                    print(result.to_json())
            else:
                print("cancelled", file=sys.stderr)
            return EXIT_CANCELLED
    if verb == "preflight":
        return run_preflight(args)
    print(f"Error: unsupported action verb '{verb}'", file=sys.stderr)
    return EXIT_INVALID_REQUEST
