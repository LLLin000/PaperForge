"""Follow-up chain runner (#167 / T6, #159 §5).

Single producer: reconcile.  After each successful layer the runner asks
reconcile (scope = this layer's successful keys) for the next layer;
handlers never hardcode follow-ups into next_actions.

Chain semantics (frozen #159/#145, #167 acceptance):
- constant depth: root = 0, children = 1, MAX_FOLLOW_UP_DEPTH = 4; deeper
  intents are reported skipped with reason `chain.depth_overflow`
- per-invocation dedupe by canonical (action_id, normalized scope):
  [A,B] ≡ [B,A]; duplicates reported skipped with `chain.duplicate`
- `--follow auto` runs automatic-local descendants inline (automatic AND
  confirmation none AND local AND non-destructive); remote / destructive /
  confirmation-required descendants stay pending with reason codes
- a confirmed parent NEVER confirms a child: children never inherit the
  root's confirmed_action_id
- cancellation halts at the next action boundary (KeyboardInterrupt
  propagates out of the chain; no further layer is derived)
- O2: a failed action produces no children (no successful publish → no
  post-publish reconcile → no downstream intents)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from paperforge.actions.registry import ACTION_REGISTRY
from paperforge.actions.runner import run_action
from paperforge.actions.types import ActionContext, ActionRequest, ActionScope

MAX_FOLLOW_UP_DEPTH = 4

# canonical action id for the scope-independent dedupe key
def canonical_scope_key(action_id: str, scope: ActionScope) -> str:
    if scope.kind == "papers":
        return f"{action_id}:papers:{','.join(sorted(scope.keys))}"
    return f"{action_id}:all"


def _scope_from_wire(scope: dict[str, Any]) -> ActionScope:
    from paperforge.actions.types import AllScope, PapersScope

    if scope.get("kind") == "papers":
        return PapersScope(tuple(scope.get("keys") or ()))
    return AllScope()


@dataclass
class ChainStep:
    depth: int
    action_id: str
    scope: dict[str, Any]
    status: str  # executed | pending | skipped
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
        fail the chain (they are reports, not failures)."""
        return all(
            step.status != "executed" or (step.result and step.result.get("ok"))
            for step in self.steps
        )

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


def _execute(
    depth: int,
    intent: dict[str, Any],
    context: ActionContext,
    confirmed_action_id: str | None,
    seen: set[str],
    steps: list[ChainStep],
    pending: list[dict[str, Any]],
    follow: str,
) -> list[tuple[int, dict[str, Any]]]:
    """Run one intent at one depth; returns derived children."""
    action_id = intent.get("action_id", "")
    scope = _scope_from_wire(intent.get("scope") or {})
    ck = canonical_scope_key(action_id, scope)

    if ck in seen:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.duplicate",
                               f"duplicate of an already-considered {ck}"))
        return []
    seen.add(ck)

    if depth >= MAX_FOLLOW_UP_DEPTH:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.depth_overflow",
                               f"follow-up depth exceeds MAX_FOLLOW_UP_DEPTH={MAX_FOLLOW_UP_DEPTH}"))
        return []

    spec = ACTION_REGISTRY.get(action_id)
    if spec is None:
        steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                               "skipped", "chain.action_unregistered",
                               f"action {action_id} is not registered"))
        return []

    # auto mode applies the inline policy at EVERY depth: remote /
    # destructive / confirmation-required intents stay pending — including
    # reconcile-emitted roots in the sync cutover.  The ONLY bypass is an
    # explicit caller confirmation of the root (--confirm); children are
    # never confirmed by their parent (frozen #145).
    if follow != "auto":
        if depth > 0:
            pending.append(intent)
            steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                                   "pending", "chain.follow_disabled",
                                   f"{action_id} not run inline (follow=none)"))
            return []
        inline, reason = True, ""  # explicit root dispatch in none mode
    else:
        if depth == 0 and confirmed_action_id == action_id:
            inline, reason = True, ""  # explicit --confirm overrides the gate
        else:
            inline, reason = _auto_inline(spec)
        if not inline:
            pending.append(intent)
            steps.append(ChainStep(depth, action_id, intent.get("scope") or {},
                                   "pending", reason,
                                   f"{action_id} not run inline (follow=auto)"))
            return []

    request = ActionRequest(action_id=action_id, scope=scope)
    confirmed = confirmed_action_id if depth == 0 else None
    try:
        result = run_action(request, context, confirmed_action_id=confirmed)
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
                           "executed", reason, "ok" if result.ok else (result.error.message if result.error else "failed"),
                           result.to_dict() if hasattr(result, "to_dict") else None))
    if not result.ok:
        # O2: no successful publish → no post-publish reconcile → no
        # children.  Sibling intents in the same layer stay independent.
        return []

    successful_keys = sorted(scope.keys) if scope.kind == "papers" else None
    children = _derive_children(context, successful_keys)
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
    follow: str = "none",
    confirmed_action_id: str | None = None,
) -> ChainResult:
    """Run the follow-up chain for the emitted root intents.

    ``root_intents`` are wire next_actions (reconcile output or an explicit
    CLI dispatch).  Layer N successes derive layer N+1 via reconcile.
    """
    chain = ChainResult()
    seen: set[str] = set()
    layer: list[tuple[int, dict[str, Any]]] = [(0, intent) for intent in root_intents]
    while layer:
        next_layer: list[tuple[int, dict[str, Any]]] = []
        for depth, intent in layer:
            next_layer.extend(
                _execute(depth, intent, context, confirmed_action_id, seen,
                         chain.steps, chain.pending, follow)
            )
        layer = next_layer
    return chain
