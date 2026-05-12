"""Unified search entry point for agent skills.
Routes: vector search -> FTS5 search -> grep based on what's available.
Always returns same JSON format regardless of backend.

Usage:
    python pf_search.py --vault VAULT_PATH --query "search text" [--limit N] [--json]

Returns JSON to stdout:
    {"ok": true, "query": "...", "engines_used": [...], "results": [...], "count": N}
    {"ok": false, "error": "..."}
"""

from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


def _find_python(vault: Path) -> str | None:
    """Same logic as pf_bootstrap: find python with paperforge installed."""
    dc_json = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if dc_json.exists():
        try:
            with open(dc_json, encoding="utf-8") as f:
                data = json.load(f)
            py = data.get("python_path", "")
            if py and Path(py).exists():
                return py
        except:
            pass

    for cand in [
        vault / ".paperforge-test-venv" / "Scripts" / "python.exe",
        vault / ".venv" / "Scripts" / "python.exe",
        vault / "venv" / "Scripts" / "python.exe",
    ]:
        if cand.exists():
            return str(cand)

    for cand in ["python", "python3"]:
        try:
            subprocess.run([cand, "--version"], capture_output=True, timeout=5)
            return cand
        except:
            continue
    return None


def _check_memory(vault: Path) -> dict:
    """Check what's available: memory db, vector db."""
    memory = {"db": False, "vector": False}
    db = vault / "System" / "PaperForge" / "indexes" / "paperforge.db"
    if db.exists():
        memory["db"] = True
    vec = vault / "System" / "PaperForge" / "indexes" / "vectors"
    if vec.exists():
        memory["vector"] = True
    return memory


def _paperforge_cmd(vault: Path, args: list[str]) -> dict | None:
    """Run a paperforge command and return parsed JSON."""
    python = _find_python(vault)
    if not python:
        return None
    cmd = [python, "-m", "paperforge", "--vault", str(vault)] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8")
        if r.returncode == 0:
            return json.loads(r.stdout)
    except:
        return None
    return None


def _grep_search(vault: Path, query: str, limit: int) -> list[dict]:
    """Fallback grep through all formal notes."""
    lit_dir = vault / "Resources" / "Literature"
    results = []
    search_lower = query.lower()
    for f in sorted(lit_dir.rglob("*.md")):
        if len(results) >= limit:
            break
        if f.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            if search_lower not in text.lower():
                continue
            title = ""
            for line in text.split("\n")[:10]:
                if line.startswith("# ") and not line.startswith("## "):
                    title = line.lstrip("# ").strip()
                    break
            results.append({
                "zotero_key": f.stem,
                "title": title or f.stem,
                "match": f.name,
                "source": "grep",
            })
        except:
            continue
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args()

    vault = Path(args.vault).resolve()
    query = args.query.strip()
    limit = args.limit

    if not query:
        print(json.dumps({"ok": False, "error": "Empty query"}))
        sys.exit(1)

    memory = _check_memory(vault)
    engines_used = []
    all_results = []
    seen_keys = set()

    # 1. Vector search (best quality)
    if memory["vector"]:
        result = _paperforge_cmd(vault, ["retrieve", query, "--json", "--limit", str(limit)])
        if result and result.get("ok"):
            engines_used.append("vector")
            for c in result.get("data", {}).get("chunks", []):
                pid = c.get("paper_id", "")
                if pid and pid not in seen_keys:
                    seen_keys.add(pid)
                    all_results.append({
                        "zotero_key": pid,
                        "citation_key": c.get("citation_key", ""),
                        "title": c.get("title", ""),
                        "year": c.get("year", ""),
                        "section": c.get("section", ""),
                        "page": c.get("page_number", ""),
                        "chunk_text": c.get("chunk_text", ""),
                        "score": c.get("score", 0),
                        "source": "vector",
                    })

    # 2. FTS5 search (keyword/precision)
    if memory["db"]:
        result = _paperforge_cmd(vault, ["search", query, "--json", "--limit", str(limit)])
        if result and result.get("ok"):
            engines_used.append("fts5")
            for p in result.get("data", {}).get("results", []):
                key = p.get("zotero_key", "")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    p["source"] = "fts5"
                    all_results.append(p)

    # 3. Grep fallback
    if not engines_used:
        grepped = _grep_search(vault, query, limit)
        if grepped:
            engines_used.append("grep")
            all_results.extend(grepped)

    output = {
        "ok": True,
        "query": query,
        "engines_used": engines_used,
        "results": all_results[:limit],
        "count": len(all_results[:limit]),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
