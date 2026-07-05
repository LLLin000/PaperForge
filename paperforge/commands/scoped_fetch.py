"""paperforge.commands.scoped_fetch — ``paperforge scoped-fetch`` gateway command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperforge.retrieval import gateway


def run(args: argparse.Namespace) -> int:
    """Execute ``scoped-fetch`` via the Layer 4 gateway."""
    vault = Path(args.vault_path)
    result = gateway.route_gateway(
        vault,
        "scoped-fetch",
        args.query,
        json_mode=bool(args.json),
        limit=getattr(args, "limit", 5),
    )
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
