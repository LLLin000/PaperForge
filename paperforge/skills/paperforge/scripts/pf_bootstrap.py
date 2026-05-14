"""PaperForge bootstrap — single entry point for agent to discover vault state.

No dependencies. Runs on ANY Python. Just reads paperforge.json + filesystem.

Usage:
    python pf_bootstrap.py              # auto-discover vault from CWD
    python pf_bootstrap.py --vault <path>

Output (JSON to stdout):
    {
        "ok": true,
        "vault_root": "D:\\...",
        "paths": {
            "literature_dir": "D:\\...\\Resources\\Literature",
            "index_path": "D:\\...\\System\\PaperForge\\indexes\\formal-library.json",
            "ocr_dir": "D:\\...\\System\\PaperForge\\ocr",
            "exports_dir": "D:\\...\\System\\PaperForge\\exports"
        },
        "domains": ["domain1", "domain2"],
        "index_summary": {"domain1": 120, "domain2": 80},
        "python_candidate": "D:\\...\\python.exe",
        "methodology_index": [
            {"id": "parameter-window-audit", "description": "比较多个研究的参数和剂量反应"},
            ...
        ]
    }

If anything fails: ok=false, error explains why.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _find_paperforge_json(start: Path) -> Path | None:
    current = start.resolve()
    for _ in range(10):
        candidate = current / "paperforge.json"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _read_pf_config(pf_json: Path) -> dict:
    with open(pf_json, encoding="utf-8") as f:
        return json.load(f)


def _find_python_with_paperforge(vault: Path, pf_cfg: dict) -> str | None:
    """Find a Python executable that has paperforge installed."""
    candidates = []

    # 1. Explicit python_path in config
    if pf_cfg.get("python_path"):
        candidates.append(Path(pf_cfg["python_path"]))

    # 2. Common venv locations inside vault
    venv_names = [".venv", ".paperforge-test-venv", "venv"]
    exe_paths = ["Scripts/python.exe", "bin/python3"]
    for vn in venv_names:
        for ep in exe_paths:
            p = vault / vn / ep
            if p.exists():
                candidates.append(p)

    for candidate in candidates:
        try:
            result = subprocess.run(
                [str(candidate), "-m", "paperforge", "--version"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            if result.returncode == 0 and "paperforge" in result.stdout.lower():
                return str(candidate)
        except Exception:
            continue

    # Fallback: try system python
    for fallback in ["python", "python3"]:
        try:
            result = subprocess.run(
                [fallback, "--version"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace",
            )
            if result.returncode == 0:
                return fallback
        except Exception:
            continue

    return None


def _scan_methodology_archive(pf_root: Path) -> list[dict]:
    """Scan methodology archive directory for available method cards."""
    archive_dir = pf_root / "methodology" / "archive"
    if not archive_dir.exists():
        return []

    methods = []
    for f in sorted(archive_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            # Extract first heading as title, first paragraph after "Use when" as description
            title = ""
            description = ""
            in_use_when = False
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped.startswith("# ") and not title:
                    title = stripped.lstrip("# ").strip()
                elif stripped.startswith("## Use when"):
                    in_use_when = True
                elif in_use_when and stripped and not stripped.startswith("#"):
                    description = stripped
                    in_use_when = False
            methods.append({
                "id": f.stem,
                "title": title or f.stem,
                "description": description or "(no description)",
            })
        except Exception:
            continue
    return methods


DEFAULTS = {
    "system_dir": "System",
    "resources_dir": "Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "Bases",
}


def resolve_cfg(raw: dict) -> dict:
    """Resolve config with vault_config nested support and legacy flat keys."""
    cfg = DEFAULTS.copy()
    nested = raw.get("vault_config", {})
    if isinstance(nested, dict):
        cfg.update({k: v for k, v in nested.items() if v})
    cfg.update({k: raw[k] for k in DEFAULTS if raw.get(k)})
    return cfg


def main():
    import argparse
    p = argparse.ArgumentParser(description="PaperForge bootstrap")
    p.add_argument("--vault", default=None, help="Vault root path (auto-detect if omitted)")
    args = p.parse_args()

    result: dict = {"ok": False}

    # --- 1. Find vault ---
    if args.vault:
        vault = Path(args.vault).resolve()
        pf_json = vault / "paperforge.json"
        if not pf_json.exists():
            result["error"] = f"paperforge.json not found at {vault}"
            json.dump(result, sys.stdout, ensure_ascii=False)
            sys.exit(0)
    else:
        pf_json = _find_paperforge_json(Path.cwd())
        if pf_json is None:
            result["error"] = "paperforge.json not found from CWD upward. Set --vault."
            json.dump(result, sys.stdout, ensure_ascii=False)
            sys.exit(0)
        vault = pf_json.parent

    result["vault_root"] = str(vault)

    # --- 2. Read config ---
    try:
        cfg = _read_pf_config(pf_json)
    except Exception as e:
        result["error"] = f"Cannot read paperforge.json: {e}"
        json.dump(result, sys.stdout, ensure_ascii=False)
        sys.exit(0)

    cfg = resolve_cfg(cfg)
    system_dir = cfg.get("system_dir", "System")
    resources_dir = cfg.get("resources_dir", "Resources")
    literature_dir = cfg.get("literature_dir", "Literature")

    # --- 3. Build paths from config ---
    pf_root = vault / system_dir / "PaperForge"

    paths = {
        "literature_dir": str(vault / resources_dir / literature_dir),
        "index_path": str(pf_root / "indexes" / "formal-library.json"),
        "ocr_dir": str(pf_root / "ocr"),
        "exports_dir": str(pf_root / "exports"),
    }
    result["paths"] = paths

    # --- 4. List domains ---
    lit_dir = Path(paths["literature_dir"])
    domains = sorted(
        [d.name for d in lit_dir.iterdir() if d.is_dir()]
    ) if lit_dir.exists() else []
    result["domains"] = domains

    # --- 5. Index summary ---
    index_path = Path(paths["index_path"])
    index_summary: dict[str, int] = {}
    if index_path.exists():
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
            items = data.get("items", [])
            if isinstance(items, dict):
                items = items.values()
            for item in items:
                d = item.get("domain", "unknown")
                index_summary[d] = index_summary.get(d, 0) + 1
        except Exception:
            pass
    result["index_summary"] = index_summary

    # --- 6. Find Python that has paperforge (best effort) ---
    py_candidate = _find_python_with_paperforge(vault, cfg)
    if py_candidate:
        result["python_candidate"] = py_candidate
        result["python_verified"] = True
    else:
        result["python_candidate"] = "python"
        result["python_verified"] = False

    # --- 7. Memory layer state ---
    memory_layer = {"available": False, "paper_count": 0, "fts_search": False, "vector_search": False}
    idx_path = Path(paths["index_path"])
    dc_json = vault / ".obsidian" / "plugins" / "paperforge" / "data.json"
    if idx_path.exists():
        try:
            with open(idx_path, encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", []) if isinstance(data, dict) else data
            memory_layer["paper_count"] = len(items)
            memory_layer["available"] = True
            memory_layer["fts_search"] = True
        except:
            pass
    if dc_json.exists():
        try:
            with open(dc_json, encoding="utf-8") as f:
                plugin_data = json.load(f)
            vector_enabled = plugin_data.get("features", {}).get("vector_db", False)
            memory_layer["vector_search"] = vector_enabled
        except:
            pass
    result["memory_layer"] = memory_layer

    # --- 8. Scan methodology archive ---
    result["methodology_index"] = _scan_methodology_archive(pf_root)

    result["ok"] = True
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
