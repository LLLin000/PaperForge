from __future__ import annotations

import json
from pathlib import Path


def read_json(path: Path):
    """Read and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, data) -> None:
    """Write JSON atomically using a temp file and replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_json(path: Path, data) -> None:
    """Write data as JSON, creating parent directories as needed."""
    write_json_atomic(path, data)


def read_jsonl(path: Path) -> list[dict]:
    """Read a newline-delimited JSON file (one JSON object per line)."""
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows
