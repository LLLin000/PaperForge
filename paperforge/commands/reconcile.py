"""`paperforge reconcile` — deficit read model + single next_actions channel
(#166 / T5, #159 §3).  Pure derivation; no side effects."""

from __future__ import annotations

import argparse

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.reconcile import reconcile


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    json_output = bool(getattr(args, "json", False))
    keys = getattr(args, "key", None) or None

    payload = reconcile(vault, keys)
    intents = payload.pop("intents", [])

    result = PFResult(
        ok=True,
        command="reconcile",
        version=PF_VERSION,
        data=payload,
        next_actions=intents,
    )
    if json_output:
        print(result.to_json())
    else:
        global_ = payload["global"]
        print(f"Reconcile — memory_ok={global_['memory_substrate_ok']} vector_ok={global_['vector_substrate_ok']}")
        print(f"Facets: {payload['facet_summary']}")
        if intents:
            for intent in intents:
                scope = intent["scope"]
                keys_txt = ",".join(scope.get("keys", [])) if scope["kind"] == "papers" else "all"
                print(f"  {intent['action_id']} ({keys_txt})")
        else:
            print("  no repair intents")
    return 0
