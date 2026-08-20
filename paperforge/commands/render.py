"""Render-layer consistency commands."""

from __future__ import annotations

import argparse
import json

from paperforge.render_audit import audit_papers


def run(args: argparse.Namespace) -> int:
    """Run the V1 read-only render audit."""
    if getattr(args, "render_subcommand", "") != "audit":
        print("unsupported render command", flush=True)
        return 2
    result = audit_papers(args.paths["ocr"], getattr(args, "keys", None), write_report=True)
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        summary = result["summary"]
        print(f"render audit: {summary['papers']} papers, {summary['issues']} issues, state={result['state']}")
        for paper in result["papers"]:
            if paper.get("issues"):
                print(f"  {paper['paper_key']}: {len(paper['issues'])} issue(s)")
    return 1 if result["state"] == "FAILED" else 0
