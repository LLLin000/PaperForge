"""Render-layer consistency commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperforge.figure_reconciliation import stage_reconciliation
from paperforge.render_audit import audit_papers


def run(args: argparse.Namespace) -> int:
    sub = getattr(args, "render_subcommand", "")
    if sub == "audit":
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
    if sub == "reconcile":
        if getattr(args, "apply_r", False):
            print("render reconcile --apply-r is gated until P0 canaries pass; running staging-only", flush=True)
            # Intentionally do not promote; fall through to staging
        ocr_root = Path(args.paths["ocr"])
        keys = getattr(args, "keys", None)
        if not keys:
            # Discover all OCR papers
            try:
                keys = [p.name for p in ocr_root.iterdir() if p.is_dir()]
            except OSError:
                keys = []
        include_pdf = bool(getattr(args, "include_pdf_media", False))
        results = []
        for key in sorted(keys):
            if not (ocr_root / key).is_dir():
                continue
            try:
                res = stage_reconciliation(ocr_root, key, include_pdf_media=include_pdf)
            except Exception as exc:
                res = {"paper_key": key, "error": f"{type(exc).__name__}: {exc}"}
            results.append(res)
        summary = {
            "papers": len(results),
            "r_prepared_staged": sum(r.get("summary", {}).get("r_prepared_staged", 0) for r in results),
            "p_preview_staged": sum(r.get("summary", {}).get("p_preview_staged", 0) for r in results),
            "production_write": False,
        }
        output = {"summary": summary, "papers": results}
        if getattr(args, "json", False):
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            msg = (
                f"render reconcile: {summary['papers']} papers, "
                f"R staged {summary['r_prepared_staged']}, "
                f"P staged {summary['p_preview_staged']}, "
                f"production_write={summary['production_write']}"
            )
            print(msg)
            for r in results:
                if r.get("summary", {}).get("r_prepared_staged") or r.get("summary", {}).get("p_preview_staged"):
                    print(f"  {r['paper_key']}: R {r['summary']['r_prepared_staged']} P {r['summary']['p_preview_staged']} -> {r.get('staging_root')}")  # noqa: E501
        return 0
    if sub == "accept-proposal":
        from paperforge.accept_proposal import accept_proposal

        result = accept_proposal(
            Path(args.paths["ocr"]),
            str(args.key),
            str(args.label),
        )
        if getattr(args, "json", False):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result.get("ok"):
                print("accepted: {} label {} -> {}".format(args.key, args.label, result.get("canonical_id")))
            else:
                print("failed: {} ({})".format(result.get("reason"), result.get("expected", "")))
        return 0 if result.get("ok") else 1
    print("unsupported render command", flush=True)
    return 2
