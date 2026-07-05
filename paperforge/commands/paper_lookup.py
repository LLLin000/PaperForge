"""paperforge.commands.paper_lookup — ``paperforge paper-lookup`` gateway command."""

from __future__ import annotations

from paperforge.retrieval import gateway


def run(args):
    """Execute ``paper-lookup`` via the Layer 4 gateway."""
    result = gateway.route_gateway(
        args.vault_path,
        "paper-lookup",
        args.query,
        json_mode=args.json,
        limit=getattr(args, "limit", 5),
    )
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
