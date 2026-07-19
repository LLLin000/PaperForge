"""paperforge.commands.paper_navigation — ``paperforge paper-navigation`` gateway command."""

from __future__ import annotations

import argparse
import json

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.retrieval import gateway


def run(args: argparse.Namespace) -> int:
    """Execute ``paper-navigation`` via the Layer 4 gateway."""
    result = gateway.route_gateway(
        args.vault_path,
        "paper-navigation",
        args.query,
        json_mode=bool(args.json),
    )
    if args.json:
        print(result.to_json())
    else:
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
    return 0 if result.ok else 1
