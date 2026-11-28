from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.io import read_json
from paperforge.core.keys import normalize_paper_keys
from paperforge.core.result import PFError, PFResult
from paperforge.memory.query import get_paper_status


def _enrich_live_ocr_meta(vault: Path, status: dict) -> dict:
    """Attach live OCR meta.json details when available."""
    zk = str(status.get("zotero_key") or "").strip()
    if not zk:
        return status
    try:
        from paperforge.config import paperforge_paths

        meta_path = paperforge_paths(vault)["ocr"] / zk / "meta.json"
        if meta_path.is_file():
            meta = read_json(meta_path)
            if isinstance(meta, dict):
                status["live_ocr"] = {
                    "ocr_status": meta.get("ocr_status", status.get("ocr_status", "")),
                    "submission_state": meta.get("submission_state", ""),
                    "ocr_job_id": meta.get("ocr_job_id", ""),
                    "provider_batch_id": meta.get("provider_batch_id", ""),
                    "error": meta.get("error", ""),
                }
    except Exception:  # noqa: BLE001
        pass
    return status


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = getattr(args, "query", None)
    raw_keys = getattr(args, "keys", None)

    if raw_keys:
        keys = normalize_paper_keys(raw_keys)
        if not keys:
            result = PFResult(
                ok=False,
                command="paper-status",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--keys cannot be empty"),
            )
            if args.json:
                print(result.to_json())
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
            return 2
        papers: list[dict] = []
        missing: list[str] = []
        try:
            for k in keys:
                st = get_paper_status(vault, k)
                if st is None:
                    missing.append(k)
                elif st.get("resolved"):
                    papers.append(_enrich_live_ocr_meta(Path(vault), st))
                else:
                    papers.append({"query": k, **st})
            result = PFResult(
                ok=True,
                command="paper-status",
                version=PF_VERSION,
                data={"papers": papers, "missing": missing, "count": len(papers)},
            )
        except Exception as exc:  # noqa: BLE001
            result = PFResult(
                ok=False,
                command="paper-status",
                version=PF_VERSION,
                error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
            )
        if args.json:
            print(result.to_json())
        elif result.ok:
            for p in result.data.get("papers", []):
                print(f"{p.get('zotero_key', p.get('query', '?'))}: ocr={p.get('ocr_status', '?')} lifecycle={p.get('lifecycle', '?')}")
            if result.data.get("missing"):
                print(f"Missing: {', '.join(result.data['missing'])}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    if not query:
        result = PFResult(
            ok=False,
            command="paper-status",
            version=PF_VERSION,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="query or --keys is required"),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 2

    try:
        status = get_paper_status(vault, query)
        if status is None:
            result = PFResult(
                ok=False,
                command="paper-status",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message=f"No paper found for: {query}",
                ),
                # T9 (#170): diagnostic data, not a command-string wire.
                data={
                    "absence_proof": "multi-path lookup exhausted",
                    "diagnostics": ["action.paper_lookup_available"],
                },
            )
        else:
            if status.get("resolved"):
                status = _enrich_live_ocr_meta(Path(vault), status)
            result = PFResult(
                ok=True,
                command="paper-status",
                version=PF_VERSION,
                data=status,
            )
    except Exception as exc:
        result = PFResult(
            ok=False,
            command="paper-status",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
            ),
        )

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            data = result.data
            if data.get("resolved"):
                print(f"Zotero Key:   {data.get('zotero_key', '')}")
                print(f"Title:        {data.get('title', '')}")
                print(f"Year:         {data.get('year', '')}")
                print(f"Lifecycle:    {data.get('lifecycle', '')}")
                print(f"Next Step:    {data.get('next_step', '')}")
            if data.get("candidates"):
                print(f"\nMultiple candidates: {len(data['candidates'])}")
                for c in data["candidates"]:
                    print(f"  - {c['zotero_key']}: {c['title']} ({c['year']})")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
