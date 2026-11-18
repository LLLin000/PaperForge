"""CLI command `paperforge annotations` — non-destructive sidecar PDF annotations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from paperforge import __version__
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


def run(args: argparse.Namespace) -> int:
    vault = Path(getattr(args, "vault_path", None) or ".").resolve()
    verb = getattr(args, "ann_verb", "")
    paper_key = str(getattr(args, "key", "") or "").strip()
    json_output = bool(getattr(args, "json", False))

    from paperforge.services.annotations_service import (
        add_annotation,
        adopt_agent_annotation,
        agent_mark_annotation,
        clear_agent_annotations,
        delete_annotation,
        get_paper_pdf_context,
        list_annotations,
        promote_to_reading_log,
        read_ocr_diagnostic_fulltext,
        update_annotation,
    )

    try:
        if verb == "pdf-info":
            data = get_paper_pdf_context(vault, paper_key)
        elif verb == "fulltext-preview":
            max_chars = int(getattr(args, "max_chars", 80000) or 80000)
            data = read_ocr_diagnostic_fulltext(vault, paper_key, max_chars=max_chars)
        elif verb == "list":
            data = {"paper_id": paper_key, "annotations": list_annotations(vault, paper_key)}
        elif verb == "add":
            rects_raw = getattr(args, "rects_json", "[]")
            rects = json.loads(rects_raw)
            tags_raw = getattr(args, "tags_json", "[]") or "[]"
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else list(tags_raw)
            style_raw = getattr(args, "style_json", "{}") or "{}"
            style = json.loads(style_raw) if isinstance(style_raw, str) else dict(style_raw)
            data = add_annotation(
                vault,
                paper_key,
                page=int(args.page),
                rects=rects,
                kind=str(getattr(args, "kind", "highlight")),
                color=str(getattr(args, "color", "yellow")),
                intent=str(getattr(args, "intent", "general")),
                exact_text=str(getattr(args, "exact_text", "") or ""),
                comment=str(getattr(args, "comment", "") or ""),
                tags=tags,
                style=style,
            )
        elif verb == "update":
            tags_arg = getattr(args, "tags_json", None)
            tags = json.loads(tags_arg) if tags_arg is not None else None
            style_arg = getattr(args, "style_json", None)
            style = (
                json.loads(style_arg)
                if isinstance(style_arg, str)
                else (dict(style_arg) if style_arg is not None else None)
            )
            rects_arg = getattr(args, "rects_json", None)
            rects = json.loads(rects_arg) if isinstance(rects_arg, str) else rects_arg
            data = update_annotation(
                vault,
                paper_key,
                str(args.ann_id),
                color=getattr(args, "color", None),
                intent=getattr(args, "intent", None),
                comment=getattr(args, "comment", None),
                tags=tags,
                style=style,
                rects=rects,
            )
        elif verb == "delete":
            data = delete_annotation(vault, paper_key, str(args.ann_id))
        elif verb == "promote":
            data = promote_to_reading_log(
                vault,
                paper_key,
                str(args.ann_id),
                usage=str(getattr(args, "usage", "evidence") or "evidence"),
                project=str(getattr(args, "project", "") or ""),
            )
        elif verb == "agent-mark":
            tags_raw = getattr(args, "tags_json", "[]") or "[]"
            tags = json.loads(tags_raw) if isinstance(tags_raw, str) else list(tags_raw)
            data = agent_mark_annotation(
                vault,
                paper_key,
                quote=str(getattr(args, "quote", "") or ""),
                figure_id=str(getattr(args, "figure_id", "") or ""),
                page_hint=getattr(args, "page_hint", None),
                section_hint=str(getattr(args, "section_hint", "") or ""),
                comment=str(getattr(args, "comment", "") or ""),
                color=str(getattr(args, "color", "purple") or "purple"),
                lens=str(getattr(args, "lens", "skeleton") or "skeleton"),
                tags=tags,
            )
        elif verb == "adopt":
            data = adopt_agent_annotation(vault, paper_key, str(args.ann_id))
        elif verb == "clear-agent":
            data = clear_agent_annotations(
                vault,
                paper_key,
                lens=str(getattr(args, "lens", "") or ""),
            )
        else:
            raise ValueError(f"Unknown annotations verb: {verb!r}")

        res = PFResult(ok=True, command="annotations", version=__version__, data=data)
        if json_output:
            print(res.to_json())
        else:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        res = PFResult(
            ok=False,
            command="annotations",
            version=__version__,
            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=str(exc)),
        )
        print(res.to_json() if json_output else f"annotations {verb} failed: {exc}")
        return 1
