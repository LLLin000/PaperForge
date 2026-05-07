"""Discussion recorder -- writes structured AI-paper Q&A into ai/ workspace directory.

Atomic append-only writes for both JSON (canonical) and Markdown (human-readable).
stdlib only -- no dependencies beyond Python standard library.

API:
    record_session(vault_path, zotero_key, agent, model, qa_pairs) -> dict

CLI:
    python -m paperforge.worker.discussion record <zotero_key> --vault <path>
        --agent <name> --model <model> [--qa-pairs <json>]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from paperforge.config import paperforge_paths
from paperforge.worker._utils import slugify_filename

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1"
_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
_MD_SEPARATOR = "---"

_CST = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return current time in ISO 8601 with timezone (CST, UTC+8)."""
    return datetime.now(_CST).isoformat()


def _today_str(iso_stamp: str) -> str:
    """Extract YYYY-MM-DD from an ISO 8601 timestamp."""
    return iso_stamp[:10]


def _find_paper_metadata(vault: Path, zotero_key: str) -> dict | None:
    """Look up paper metadata from the canonical index.

    Returns dict with 'domain' and 'title' and 'ai_path' or None if not found.
    """
    try:
        paths = paperforge_paths(vault)
    except Exception as exc:
        logger.warning("Failed to resolve PaperForge paths: %s", exc)
        return None

    index_path = paths.get("index")
    if not index_path or not index_path.exists():
        logger.warning("Canonical index does not exist: %s", index_path)
        return None

    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read canonical index: %s", exc)
        return None

    items = index.get("items", []) if isinstance(index, dict) else []
    for entry in items:
        if entry.get("zotero_key") == zotero_key:
            return {
                "domain": entry.get("domain", ""),
                "title": entry.get("title", ""),
                "ai_path": entry.get("ai_path", ""),
            }
    return None


def _build_ai_dir(vault: Path, domain: str, key: str, title: str) -> Path:
    """Construct the ai/ directory path for a paper's workspace.

    Pattern: Literature/{domain}/{key} - {title_slug}/ai/
    Uses paperforge_paths for portable path resolution (per D-01).
    """
    try:
        paths = paperforge_paths(vault)
        lit_root = paths["literature"]
    except Exception:
        # Fallback to default structure if config loading fails
        lit_root = vault / "03_Resources" / "Literature"
    title_slug = slugify_filename(title) if title else key
    ai_dir = lit_root / domain / f"{key} - {title_slug}" / "ai"
    return ai_dir


def _build_session(
    agent: str,
    model: str,
    zotero_key: str,
    paper_title: str,
    domain: str,
    qa_pairs: list[dict],
) -> dict:
    """Build a session object per D-11."""
    return {
        "session_id": str(uuid.uuid4()),
        "agent": agent,
        "model": model,
        "started": _now_iso(),
        "paper_key": zotero_key,
        "paper_title": paper_title,
        "domain": domain,
        "qa_pairs": list(qa_pairs),
    }


def _atomic_write_json(target_path: Path, envelope: dict) -> None:
    """Atomically write JSON file via tempfile + os.replace.

    Uses ensure_ascii=False for CJK support, newline='\\n' for consistent
    line endings on Windows.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"

    fd, tmp_path_str = tempfile.mkstemp(
        suffix=".json",
        prefix="discussion_",
        dir=str(target_path.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        fd = None
        os.replace(tmp_path_str, str(target_path))
    except Exception:
        # Cleanup temp file on failure
        if fd is not None:
            os.close(fd)
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _build_md_header(paper_title: str) -> str:
    return f"# AI Discussion Record: {paper_title}\n\n"


def _build_md_session(session: dict) -> str:
    """Format a session entry as human-readable Markdown."""
    started = session["started"]
    date_str = _today_str(started)
    agent = session["agent"]
    model = session["model"]
    lines = [f"## {date_str} -- {agent} ({model})\n"]
    for qa in session["qa_pairs"]:
        lines.append(f"**问题:** {qa['question']}")
        lines.append(f"**解答:** {qa['answer']}\n")
    lines.append(f"{_MD_SEPARATOR}\n")
    return "\n".join(lines)


def _md_content(existing: str, header: str, session_md: str) -> str:
    """Append session markdown to existing content or create new."""
    if existing.strip():
        return existing.rstrip("\n") + "\n\n" + session_md
    return header + session_md


def _atomic_write_md(target_path: Path, content: str) -> None:
    """Atomically write Markdown file via tempfile + os.replace."""
    target_path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path_str = tempfile.mkstemp(
        suffix=".md",
        prefix="discussion_",
        dir=str(target_path.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        fd = None
        os.replace(tmp_path_str, str(target_path))
    except Exception:
        if fd is not None:
            os.close(fd)
        if tmp_path.exists():
            tmp_path.unlink()
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_session(
    vault_path: Path,
    zotero_key: str,
    agent: str,
    model: str,
    qa_pairs: list[dict],
) -> dict:
    """Record an AI-paper discussion session.

    Creates or appends to ai/discussion.json (canonical) and
    ai/discussion.md (human-readable) with atomic writes.

    Args:
        vault_path: Path to the Obsidian vault root.
        zotero_key: Zotero citation key (8 characters).
        agent: Agent name (e.g. "pf-paper").
        model: Model identifier (e.g. "gpt-4").
        qa_pairs: List of dicts with keys: question, answer, source, timestamp.

    Returns:
        dict with "status": "ok"|"error" and relevant paths or error message.
    """
    # --- Validation ---
    try:
        vault_path = Path(vault_path).expanduser().resolve()
    except Exception as exc:
        return {"status": "error", "message": f"Invalid vault path: {exc}"}

    if not vault_path.exists():
        return {"status": "error", "message": f"Vault path does not exist: {vault_path}"}
    if not vault_path.is_dir():
        return {"status": "error", "message": f"Vault path is not a directory: {vault_path}"}

    if not zotero_key or not isinstance(zotero_key, str):
        return {"status": "error", "message": "zotero_key must be a non-empty string"}

    if not isinstance(qa_pairs, list):
        return {"status": "error", "message": "qa_pairs must be a list"}

    # --- Find paper metadata ---
    try:
        meta = _find_paper_metadata(vault_path, zotero_key)
    except Exception as exc:
        logger.warning("Error finding paper metadata: %s", exc)
        return {"status": "error", "message": f"Error finding paper metadata: {exc}"}

    if meta is None:
        return {"status": "error", "message": f"Paper not found in canonical index: {zotero_key}"}

    domain = meta["domain"]
    paper_title = meta["title"] or zotero_key

    # --- Build paths (WS-03: use ai_path from canonical index) ---
    ai_path_str = meta.get("ai_path", "")
    if ai_path_str:
        ai_dir = vault_path / ai_path_str.replace("/", "\\") if os.name == "nt" else vault_path / ai_path_str
    else:
        # Fallback: construct from metadata
        ai_dir = _build_ai_dir(vault_path, domain, zotero_key, paper_title)

    json_path = ai_dir / "discussion.json"
    md_path = ai_dir / "discussion.md"

    # --- Build session object ---
    try:
        session = _build_session(agent, model, zotero_key, paper_title, domain, qa_pairs)
    except Exception as exc:
        return {"status": "error", "message": f"Error building session: {exc}"}

    # --- Write discussion.json (atomic, append) ---
    try:
        existing_sessions = []
        if json_path.exists():
            try:
                existing_data = json.loads(json_path.read_text(encoding="utf-8"))
                existing_sessions = existing_data.get("sessions", [])
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Corrupted discussion.json, starting fresh: %s", exc)
                existing_sessions = []

        envelope = {
            "schema_version": "1",
            "paper_key": zotero_key,
            "sessions": [*existing_sessions, session],
        }
        _atomic_write_json(json_path, envelope)
    except Exception as exc:
        logger.warning("Failed to write discussion.json: %s", exc)
        return {"status": "error", "message": f"Failed to write discussion.json: {exc}"}

    # --- Write discussion.md (atomic, append) ---
    try:
        existing_md = ""
        if md_path.exists():
            try:
                existing_md = md_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("Could not read existing discussion.md: %s", exc)
                existing_md = ""

        header = _build_md_header(paper_title)
        session_md = _build_md_session(session)
        content = _md_content(existing_md, header, session_md)
        _atomic_write_md(md_path, content)
    except Exception as exc:
        logger.warning("Failed to write discussion.md: %s", exc)
        # JSON already written; return partial success
        return {
            "status": "error",
            "message": f"Failed to write discussion.md: {exc}",
            "json_path": str(json_path),
        }

    return {
        "status": "ok",
        "json_path": str(json_path),
        "md_path": str(md_path),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_cli_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m paperforge.worker.discussion",
        description="Record AI-paper discussion sessions",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    record_p = sub.add_parser("record", help="Record a discussion session")
    record_p.add_argument("zotero_key", help="Zotero citation key")
    record_p.add_argument("--vault", required=True, help="Path to Obsidian vault")
    record_p.add_argument("--agent", required=True, help="Agent name (e.g. pf-paper)")
    record_p.add_argument("--model", required=True, help="Model identifier")
    record_p.add_argument(
        "--qa-pairs",
        default="[]",
        help='JSON array of Q&A pairs',
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns exit code."""
    # Ensure UTF-8 output on Windows (console may use cp936/GBK)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = _build_cli_parser()
    args = parser.parse_args(argv)

    if args.command == "record":
        vault_path = Path(args.vault)
        try:
            qa_pairs = json.loads(args.qa_pairs)
        except json.JSONDecodeError as exc:
            result = {"status": "error", "message": f"Invalid --qa-pairs JSON: {exc}"}
            print(json.dumps(result, ensure_ascii=False))
            return 1

        result = record_session(
            vault_path=vault_path,
            zotero_key=args.zotero_key,
            agent=args.agent,
            model=args.model,
            qa_pairs=qa_pairs,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "ok" else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
