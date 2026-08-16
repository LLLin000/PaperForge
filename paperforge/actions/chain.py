"""Follow-up chain runner (#167 / T6, #159 §5).

Single producer: reconcile.  After each successful layer the runner asks
reconcile (scope = the layer's actual SUCCESSFUL keys — #167 P0-5 seam,
never the bare requested scope) for the next layer; handlers never
hardcode follow-ups into next_actions.

Chain semantics (frozen #159/#145, #167 acceptance + closure corrective):
- constant depth: root = 0, children = 1; depths 0..MAX_FOLLOW_UP_DEPTH
  are legal, depth > MAX is rejected (`chain.depth_overflow`)
- per-invocation dedupe by canonical (action_id, NORMALIZED scope):
  [A,A,B] ≡ [B,A]; duplicates reported skipped with `chain.duplicate`
- `--follow auto` runs automatic-local descendants inline (automatic AND
  confirmation none AND local AND non-destructive); remote / destructive /
  confirmation-required descendants stay pending with reason codes
- a confirmed parent NEVER confirms a child; explicit root confirmation
  belongs to the caller (T2 run_action) — this runner only sees intents
  that are ALREADY authorized for its layer
- cancellation halts at the next action boundary (KeyboardInterrupt
  propagates out of the chain; no further layer is derived)
- O2: a failed action produces no children (no successful publish → no
  post-publish reconcile → no downstream intents)
- W2 (#158/#167 P0-2): every DISPATCHED action settles an overwrite-only
  last-attempt record keyed by semantic attempt digest; pre-dispatch
  pending/skipped intents are never recorded as attempts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.runner import run_action
from paperforge.actions.types import (
    ActionContext,
    ActionRequest,
    ActionScope,
    scope_from_dict,
)

MAX_FOLLOW_UP_DEPTH = 4


def canonical_scope_key(action_id: str, scope: ActionScope) -> str:
    if scope.kind == "papers":
        return f"{action_id}:papers:{','.join(sorted(set(scope.keys)))}"
    return f"{action_id}:all"


@dataclass
class ChainStep:
    depth: int
    action_id: str
    scope: dict
    status: str  # executed | pending | skipped | failed
    reason_code: str
    reason: str
    result: dict[str, Any] | None = None


@dataclass
class ChainResult:
    steps: list[ChainStep] = field(default_factory=list)
    pending: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when every EXECUTED step succeeded; pending/skipped never
        fail the chain (they are reports, not failures); failed steps do."""
        return all(
            step.status != "executed" or (step.result and step.result.get("ok"))
            for step in self.steps
        ) and all(step.status != "failed" for step in self.steps)

    def to_wire(self) -> dict:
        return {
            "schema_version": 1,
            "module": "chain",
            "steps": [
                {
                    "depth": s.depth,
                    "action_id": s.action_id,
                    "scope": s.scope,
                    "status": s.status,
                    "reason_code": s.reason_code,
                    "reason": s.reason,
                    "result": s.result,
                }
                for s in self.steps
            ],
            "pending": self.pending,
        }


# Default producer seam: reconcile is the single source of intents.
def _reconcile_producer(vault: Path, keys: list[str] | None) -> Any:
    from paperforge.reconcile import reconcile

    return reconcile(vault, keys)


def _auto_inline(spec) -> tuple[bool, str]:
    """(inline?, reason_code) — auto mode runs automatic-local descendants
    only.  First matching gate wins."""
    if spec.impact == "destructive":
        return False, "chain.destructive"
    if spec.cost == "remote_possible":
        return False, "chain.remote_spend"
    if spec.confirmation == "required":
        return False, "chain.confirmation_required"
    if not spec.automatic:
        return False, "chain.not_automatic"
    return True, ""


def _settle_w2(context: ActionContext, intent: dict[str, Any], result: Any) -> None:
    """#167 P0-2: overwrite the last-attempt record for a DISPATCHED action.
    Only dispatched attempts settle — pre-dispatch pending/skipped intents
    never become failed records (a confirmation-required intent is not a
    failed attempt)."""
    from paperforge.actions.types import scope_from_dict as _s
    from paperforge.reconcile import record_last_attempt, semantic_attempt_digest

    try:
        scope = _s(intent.get("scope") or {})
    except ValueError:
        return
    digest = semantic_attempt_digest(context.vault, intent)
    record_last_attempt(
        context.vault,
        action_id=str(intent.get("action_id", "")),
        scope=scope,
        input_digest=digest,
        outcome="succeeded" if getattr(result, "ok", False) else "failed",
        error_code=(
            getattr(result.error, "code", "") if getattr(result, "error", None) else ""
        ),
    )


def _successful_keys(scope: ActionScope, result: Any) -> list[str] | None:
    """#167 P0-5 successful-scope seam: per-key results report their own
    successful keys; all-or-nothing results fall back to the request scope.
    Never action-id branching."""
    per_key = getattr(result, "successful_keys", None)
    if per_key is not None:
        return sorted(set(per_key))
    if scope.kind == "papers":
        return sorted(set(scope.keys))
    return None


def _execute(
    depth: int,
    intent: dict[str, Any],
    context: ActionContext,
    seen: set[str],
    steps: list[ChainStep],
    pending: list[dict[str, Any]],
) -> list[tuple[int, dict[str, Any]]]:
    """Run one intent at one depth; returns derived children."""
    action_id = intent.get("action_id", "")
    try:
        scope = scope_from_dict(intent.get("scope") or {})
    except ValueError:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.scope_invalid",
                               f"unknown scope kind in {action_id} intent"))
        return []
    ck = canonical_scope_key(action_id, scope)

    if ck in seen:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.duplicate",
                               f"duplicate of an already-considered {ck}"))
        return []
    seen.add(ck)

    if depth > MAX_FOLLOW_UP_DEPTH:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.depth_overflow",
                               f"follow-up depth {depth} exceeds MAX_FOLLOW_UP_DEPTH={MAX_FOLLOW_UP_DEPTH}"))
        return []

    spec = ACTION_REGISTRY.get(action_id)
    if spec is None:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.action_unregistered",
                               f"action {action_id} is not registered"))
        return []

    # This runner only sees intents that are already authorized for its
    # layer (explicit root confirmation happens in the T2 pipeline; sync's
    # reconcile roots run the inline gate).  Children are never confirmed
    # by their parent — a confirmation-required descendant stays pending.
    inline, reason = _auto_inline(spec)
    if not inline:
        pending.append(intent)
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "pending", reason,
                               f"{action_id} not run inline"))
        return []

    request = ActionRequest(action_id=action_id, scope=scope)
    try:
        result = run_action(request, context, confirmed_action_id=None)
    except KeyboardInterrupt:
        # Cancellation halts at the next action boundary: propagate — no
        # further layer is derived.
        raise
    except Exception as exc:  # noqa: BLE001 — pre-dispatch failure (ActionError
        # or preflight/handler plumbing) records a failed step and derives
        # NO children; it never crashes the chain (O2 spirit).
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "failed", getattr(exc, "code", "chain.pre_dispatch_failed"),
                               str(exc)))
        return []

    steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                           "executed", reason,
                           "ok" if result.ok else (result.error.message if result.error else "failed"),
                           result.to_dict() if hasattr(result, "to_dict") else None))
    # W2: dispatched actions settle the last-attempt record (success or
    # failure) so a periodic trigger never blind-retries identical input.
    _settle_w2(context, intent, result)
    if not result.ok:
        # P0-3 (owner review): a batch with a successful subset must NOT
        # stall the whole pipeline — 24/25 done + 1 pending/failed still
        # advances the 24.  Only the non-succeeded keys are excluded; with
        # no successes this stays O2 (no publish → no children).
        successful = _successful_keys(scope, result)
        if not successful:
            return []
        children = _derive_children(context, successful)
        return [(depth + 1, child) for child in children]

    successful = _successful_keys(scope, result)
    children = _derive_children(context, successful)
    return [(depth + 1, child) for child in children]


def _derive_children(context: ActionContext, keys: list[str] | None) -> list[dict[str, Any]]:
    """Post-publish reconcile (single producer) for the successful scope."""
    try:
        result = _reconcile_producer(context.vault, keys)
    except Exception:  # noqa: BLE001 — a broken producer must not fail sync
        return []
    if not getattr(result, "ok", True):
        return []
    return list(result.next_actions or [])


def run_chain(
    root_intents: list[dict[str, Any]],
    context: ActionContext,
    *,
    root_depth: int = 0,
) -> ChainResult:
    """Run the follow-up chain for the emitted root intents.

    ``root_intents`` are wire next_actions (reconcile output, or the
    descendants of an explicitly dispatched CLI root — pass root_depth=1 in
    that case, because the T2 pipeline already consumed the root).  Layer N
    successes derive layer N+1 via reconcile.

    The inline policy is unconditional (automatic-local only; everything
    else pending) — the caller decides whether the chain runs at all
    (CLI --follow auto / sync terminal mode), never which intents inline.
    """
    chain = ChainResult()
    seen: set[str] = set()
    layer: list[tuple[int, dict[str, Any]]] = [(root_depth, intent) for intent in root_intents]
    while layer:
        next_layer: list[tuple[int, dict[str, Any]]] = []
        for depth, intent in layer:
            next_layer.extend(_execute(depth, intent, context, seen, chain.steps, chain.pending))
        layer = next_layer
    return chain
