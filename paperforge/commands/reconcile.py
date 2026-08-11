"""`paperforge reconcile` — deficit read model + single next_actions channel
(#166 / T5, #159 §3).  Pure derivation; no side effects.  The intent
projection lives on PFResult.next_actions — no separate wire."""

from __future__ import annotations

import argparse

from paperforge.reconcile import reconcile


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    json_output = bool(getattr(args, "json", False))
    keys = getattr(args, "key", None) or None

    result = reconcile(vault, keys)
    if json_output:
        print(result.to_json())
    else:
        data = result.data
        global_ = data["global"]
        print(f"Reconcile — memory_ok={global_['memory_substrate_ok']} vector_ok={global_['vector_substrate_ok']}")
        print(f"Facets: {data['facet_summary']}")
        if data["diagnostics"]:
            for diag in data["diagnostics"]:
                print(f"  diag: {diag}")
        if result.next_actions:
            for intent in result.next_actions:
                scope = intent["scope"]
                keys_txt = ",".join(scope.get("keys", [])) if scope["kind"] == "papers" else "all"
                print(f"  {intent['action_id']} ({keys_txt})")
        else:
            print("  no repair intents")
    return 0
