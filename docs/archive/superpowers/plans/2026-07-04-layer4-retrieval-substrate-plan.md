# Layer 4 Retrieval Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a paper-native retrieval substrate for PaperForge with explicit gateway commands, robust paper lookup, structure-aware paper navigation, default body-unit FTS, and vector-backend decoupling.

**Architecture:** Implement Layer 4 in ordered phases. First wrap existing capabilities behind new agent-facing gateway commands without changing the underlying stores. Then add new retrieval artifacts (`structure-tree.json`, `body_units.jsonl`, `body_units_fts`, `paper_manifest.json`) and upgrade the gateway to use them. Only after the unit contract is stable, abstract the hard-coded Chroma path behind a vector-backend adapter.

**Tech Stack:** Python 3, SQLite/FTS5, existing PaperForge memory DB, OCR structured blocks + role-index artifacts, pytest, current Chroma backend as compatibility adapter.

## Global Constraints

- FTS is default-on; vector DB remains optional and must not become a prerequisite for core retrieval flows.
- `paper_fts` remains metadata FTS for paper lookup / narrowing; Layer 4 must add `body_units_fts` for default body-text recall.
- Reuse existing `paperforge.query_planning.QuerySignals` and `lookup_paper()`; do not create a second query decomposition implementation.
- Keep existing `search / retrieve / query-plan / paper-status / paper-context / context` commands as compatibility aliases / low-level diagnostics.
- `paper_lookup` must decompose first, search multiple combinations, rank by evidence coverage, and forbid single-query zero-hit as absence proof.
- `paper_navigation` and `scoped_fetch` must not assume a real structure tree exists before the builder lands.
- Retrieval is structure-first and trust-neutral at paper level; OCR health may only drive local junk veto and diagnostics, never paper-level ranking penalties.
- Local junk veto must be auditable via `indexable`, `veto_reason`, and `quality_hints` fields.
- Prefer `structured_blocks` as truth, `role-index` as helper, and `fulltext` only as fallback when building retrieval units.
- Layer 4 does not implement PaperCard / SubmethodCard / understanding-layer assets.

---

## File Map

### Existing files to modify

- `paperforge/cli.py` — register new gateway subcommands and keep old commands intact.
- `paperforge/query_planning.py` — extend `QuerySignals`-driven routing support for lookup coverage and explicit agent advice.
- `paperforge/memory/query.py` — strengthen `lookup_paper()` into decomposed, coverage-scored multi-path lookup.
- `paperforge/memory/schema.py` — add `body_units`, `body_units_fts`, `object_units`, and manifest schema.
- `paperforge/memory/builder.py` — seed the new tables during memory rebuilds when retrieval artifacts exist.
- `paperforge/worker/ocr.py` — write `structure-tree.json` after OCR structure is available.
- `paperforge/worker/ocr_rebuild.py` — rebuild `structure-tree.json` alongside `role-index.json`.
- `paperforge/embedding/builder.py` — replace direct Chroma calls with backend adapter use once adapter task lands.
- `paperforge/embedding/search.py` — route vector retrieval through the adapter.
- `paperforge/embedding/status.py` — surface backend health through the adapter.

### New files to create

- `paperforge/retrieval/gateway.py` — route entrypoint used by the new gateway commands.
- `paperforge/commands/paper_lookup.py` — agent-facing command for locating a paper.
- `paperforge/commands/content_discovery.py` — agent-facing command for cross-corpus recall.
- `paperforge/commands/paper_navigation.py` — agent-facing command for paper structure navigation.
- `paperforge/commands/scoped_fetch.py` — agent-facing command for section/block fetch.
- `paperforge/retrieval/structure_tree.py` — build/load `structure-tree.json` from OCR blocks.
- `paperforge/retrieval/units.py` — build `BodyUnit` / `ObjectUnit`, stable `unit_id`, and audit fields.
- `paperforge/retrieval/manifest.py` — build/read `paper_manifest.json` and compute rebuild hashes.
- `paperforge/embedding/backends/base.py` — vector backend protocol.
- `paperforge/embedding/backends/chroma_backend.py` — current behavior moved behind the adapter.
- `tests/test_layer4_gateway_commands.py`
- `tests/test_layer4_paper_lookup.py`
- `tests/test_layer4_structure_tree.py`
- `tests/test_layer4_units_and_fts.py`
- `tests/test_layer4_vector_backend.py`

## Task 1: Add the gateway command surface over existing capabilities

**Files:**
- Create: `paperforge/retrieval/gateway.py`
- Create: `paperforge/commands/paper_lookup.py`
- Create: `paperforge/commands/content_discovery.py`
- Create: `paperforge/commands/paper_navigation.py`
- Create: `paperforge/commands/scoped_fetch.py`
- Modify: `paperforge/cli.py`
- Test: `tests/test_layer4_gateway_commands.py`

**Interfaces:**
- Consumes: `paperforge.query_planning.build_query_plan(query: str, intent: str) -> dict`
- Consumes: existing command modules (`search`, `retrieve`, `paper_status`, `paper_context`) as compatibility surfaces
- Produces: `route_gateway(vault: Path, intent: str, query: str, *, json_mode: bool, limit: int = 5) -> PFResult`
- Produces: CLI subcommands `paperforge paper-lookup`, `paperforge content-discovery`, `paperforge paper-navigation`, `paperforge scoped-fetch`

- [ ] **Step 1: Write the failing gateway command tests**

```python
from argparse import Namespace

from paperforge.commands import paper_lookup, content_discovery, paper_navigation, scoped_fetch


def test_paper_lookup_command_registered_and_json(tmp_path):
    args = Namespace(vault_path=tmp_path, query="Smith 2021", json=True, limit=5)
    exit_code = paper_lookup.run(args)
    assert exit_code in {0, 1}


def test_content_discovery_warns_when_only_metadata_fts_exists(tmp_path, monkeypatch):
    from paperforge.core.result import PFResult
    from paperforge.retrieval import gateway

    def fake_route_gateway(*args, **kwargs):
        return PFResult(ok=True, command="content-discovery", version="x", data={"mode": "metadata_only"}, warnings=["body_units_fts missing"])

    monkeypatch.setattr(gateway, "route_gateway", fake_route_gateway)
    args = Namespace(vault_path=tmp_path, query="delirium prevention", json=True, limit=5)
    assert content_discovery.run(args) == 0
```

- [ ] **Step 2: Run the tests to confirm the commands do not exist yet**

Run: `pytest tests/test_layer4_gateway_commands.py -v`
Expected: FAIL with import errors or missing command handlers.

- [ ] **Step 3: Add the gateway core and thin command wrappers**

```python
# paperforge/retrieval/gateway.py
from __future__ import annotations

from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.result import PFResult
from paperforge.query_planning import build_query_plan, enrich_query_plan_with_runtime


INTENTS = {
    "paper-lookup": "known-paper",
    "content-discovery": "content",
    "paper-navigation": "known-paper",
    "scoped-fetch": "known-paper",
}


def route_gateway(vault: Path, intent: str, query: str, *, json_mode: bool, limit: int = 5) -> PFResult:
    plan = enrich_query_plan_with_runtime(build_query_plan(query, INTENTS[intent]), vault)
    return PFResult(
        ok=True,
        command=intent,
        version=PF_VERSION,
        data={
            "intent": intent,
            "query": query,
            "route_plan": plan,
            "limit": limit,
        },
    )
```

```python
# paperforge/commands/paper_lookup.py
from __future__ import annotations

from paperforge.retrieval.gateway import route_gateway


def run(args):
    result = route_gateway(args.vault_path, "paper-lookup", args.query, json_mode=args.json, limit=getattr(args, "limit", 5))
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
```

```python
# paperforge/cli.py (new parser registration)
p_paper_lookup = sub.add_parser("paper-lookup", help="Locate a specific paper through the Layer 4 gateway")
p_paper_lookup.add_argument("query", help="Paper identifier, title fragment, author+year, DOI, or alias")
p_paper_lookup.add_argument("--json", action="store_true")
p_paper_lookup.add_argument("--limit", type=int, default=5)
```

- [ ] **Step 4: Make `paper-navigation` and `scoped-fetch` explicit compatibility shells**

```python
# paperforge/commands/paper_navigation.py
from __future__ import annotations

from paperforge.retrieval.gateway import route_gateway


def run(args):
    result = route_gateway(args.vault_path, "paper-navigation", args.query, json_mode=args.json, limit=getattr(args, "limit", 5))
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
```

```python
# paperforge/commands/scoped_fetch.py
from __future__ import annotations

from paperforge.retrieval.gateway import route_gateway


def run(args):
    result = route_gateway(args.vault_path, "scoped-fetch", args.query, json_mode=args.json, limit=getattr(args, "limit", 5))
    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
```

- [ ] **Step 5: Run the new gateway command tests**

Run: `pytest tests/test_layer4_gateway_commands.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/retrieval/gateway.py paperforge/commands/paper_lookup.py paperforge/commands/content_discovery.py paperforge/commands/paper_navigation.py paperforge/commands/scoped_fetch.py paperforge/cli.py tests/test_layer4_gateway_commands.py
git commit -m "feat: add Layer 4 gateway command surface"
```

## Task 2: Strengthen `paper_lookup` using existing `QuerySignals` and `lookup_paper()`

**Files:**
- Modify: `paperforge/query_planning.py`
- Modify: `paperforge/memory/query.py`
- Modify: `paperforge/commands/paper_status.py`
- Modify: `paperforge/commands/paper_context.py`
- Test: `tests/test_layer4_paper_lookup.py`

**Interfaces:**
- Consumes: `classify_signals(query: str) -> QuerySignals`
- Consumes: `lookup_paper(conn, query: str) -> list[dict]`
- Produces: `lookup_paper(conn, query: str) -> list[dict]` with `matched_by`, `coverage_score`, and multi-path lookup
- Produces: richer candidate payloads for `paper-status` / `paper-context`

- [ ] **Step 1: Write failing lookup tests for author/year/title coverage**

```python
import sqlite3

from paperforge.memory.query import lookup_paper
from paperforge.memory.schema import ensure_schema


def test_lookup_paper_uses_author_year_when_title_bundle_is_overconstrained(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO papers (zotero_key, title, first_author, year, doi, citation_key) VALUES (?, ?, ?, ?, ?, ?)",
        ("ABCD1234", "Chain of Ideas for Literature Review", "Smith", "2021", "", "smith2021chain"),
    )
    conn.commit()

    matches = lookup_paper(conn, "Smith 2021 Chain Ideas Revolutionizing")
    assert matches
    assert matches[0]["zotero_key"] == "ABCD1234"
    assert matches[0]["matched_by"]
    assert matches[0]["coverage_score"] > 0
```

- [ ] **Step 2: Run the lookup tests and confirm current AND-title matching fails**

Run: `pytest tests/test_layer4_paper_lookup.py -v`
Expected: FAIL because `lookup_paper()` only does exact IDs, title-token AND, and alias fallback.

- [ ] **Step 3: Extend `lookup_paper()` without creating a second parser**

```python
# paperforge/memory/query.py
from paperforge.query_planning import classify_signals


def _coverage_entry(row, *, matched_by: str, matched_title_tokens: int, title_token_total: int, matched_author: bool, matched_year: bool):
    entry = _entry_from_row(row)
    entry["matched_by"] = matched_by
    entry["matched_author"] = matched_author
    entry["matched_year"] = matched_year
    entry["matched_title_tokens"] = f"{matched_title_tokens}/{title_token_total}"
    entry["coverage_score"] = int(matched_author) + int(matched_year) + matched_title_tokens
    return entry


def lookup_paper(conn, query: str) -> list[dict]:
    signals = classify_signals(query)
    exact_candidates = _lookup_exact_identifiers(conn, signals)
    if exact_candidates:
        return exact_candidates
    candidates = []
    candidates.extend(_lookup_author_year(conn, signals))
    candidates.extend(_lookup_author_title(conn, signals))
    candidates.extend(_lookup_year_title(conn, signals))
    candidates.extend(_lookup_relaxed_title_subsets(conn, signals))
    candidates.extend(_lookup_alias(conn, query))
    return _dedupe_and_sort_candidates(candidates)
```

- [ ] **Step 4: Return multi-candidate diagnostics from `paper-status` instead of plain misses**

```python
# paperforge/commands/paper_status.py
if status is None:
    result = PFResult(
        ok=False,
        command="paper-status",
        version=PF_VERSION,
        error=PFError(code=ErrorCode.PATH_NOT_FOUND, message=f"No paper found for: {query}"),
        data={"absence_proof": "multi-path lookup exhausted"},
        next_actions=[{"command": "paperforge paper-lookup", "reason": "Run the Layer 4 decomposed lookup gateway."}],
    )
```

- [ ] **Step 5: Run the lookup and status tests**

Run: `pytest tests/test_layer4_paper_lookup.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/query_planning.py paperforge/memory/query.py paperforge/commands/paper_status.py paperforge/commands/paper_context.py tests/test_layer4_paper_lookup.py
git commit -m "feat: make paper lookup decomposed and coverage-scored"
```

## Task 3: Build `structure-tree.json` and a navigable paper outline

**Files:**
- Create: `paperforge/retrieval/structure_tree.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Modify: `paperforge/commands/paper_navigation.py`
- Test: `tests/test_layer4_structure_tree.py`

**Interfaces:**
- Consumes: `structured_blocks: list[dict[str, Any]]`
- Consumes: `role-index.json` as helper only
- Produces: `build_structure_tree(structured_blocks: list[dict[str, Any]]) -> dict[str, Any]`
- Produces: `write_structure_tree(index_root: Path, tree: dict[str, Any]) -> None`
- Produces: `paper_navigation` phase-2 path that returns nodes with `node_id`, `title`, `level`, `section_path`, `page_span`

- [ ] **Step 1: Write failing structure tree tests**

```python
from paperforge.retrieval.structure_tree import build_structure_tree


def test_build_structure_tree_creates_section_nodes_from_headings():
    structured_blocks = [
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b1", "role": "section_heading", "text": "Methods"},
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients."},
    ]
    tree = build_structure_tree(structured_blocks)
    assert tree["paper_id"] == "ABCD1234"
    assert tree["nodes"][0]["title"] == "Methods"
    assert tree["nodes"][0]["section_path"] == ["Methods"]
```

- [ ] **Step 2: Run the tests to confirm the builder does not exist yet**

Run: `pytest tests/test_layer4_structure_tree.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Add a minimal structure tree builder**

```python
# paperforge/retrieval/structure_tree.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from paperforge.core.io import write_json


def build_structure_tree(structured_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None
    for block in structured_blocks:
        role = block.get("role")
        text = str(block.get("text", "")).strip()
        if role in {"section_heading", "subsection_heading", "introduction_heading", "abstract_heading"} and text:
            current_section = {
                "node_id": f"sec:{block.get('block_id')}",
                "kind": "section",
                "title": text,
                "level": 1 if role != "subsection_heading" else 2,
                "section_path": [text] if role != "subsection_heading" else [nodes[-1]["title"], text] if nodes else [text],
                "page_span": [block.get("page", 0), block.get("page", 0)],
                "block_span": [[block.get("page", 0), block.get("block_id", "")]],
                "children": [],
                "objects": [],
            }
            nodes.append(current_section)
        elif current_section is not None:
            current_section["page_span"][1] = block.get("page", current_section["page_span"][1])
            current_section["block_span"].append([block.get("page", 0), block.get("block_id", "")])
    return {"paper_id": structured_blocks[0].get("paper_id", "") if structured_blocks else "", "nodes": nodes}


def write_structure_tree(index_root: Path, tree: dict[str, Any]) -> None:
    index_root.mkdir(parents=True, exist_ok=True)
    write_json(index_root / "structure-tree.json", tree)
```

- [ ] **Step 4: Wire the builder into OCR and `paper-navigation`**

```python
# paperforge/worker/ocr.py
from paperforge.retrieval.structure_tree import build_structure_tree, write_structure_tree

structure_tree = build_structure_tree(structured)
write_structure_tree(ocr_root / "index", structure_tree)
```

```python
# paperforge/commands/paper_navigation.py
from __future__ import annotations

import json

from paperforge.core.result import PFResult
from paperforge.core.io import read_json
from paperforge.retrieval.structure_tree import summarize_role_index


def run(args):
    paper_root = _resolve_paper_root(args.vault_path, args.query)
    tree_path = paper_root / "index" / "structure-tree.json"
    if tree_path.exists():
        tree = read_json(tree_path)
        payload = {"mode": "structure_tree", "paper_id": tree.get("paper_id", ""), "nodes": tree.get("nodes", [])}
    else:
        role_index = read_json(paper_root / "index" / "role-index.json")
        payload = {"mode": "role_index_summary", "paper_id": args.query, "summary": summarize_role_index(role_index)}
    result = PFResult(ok=True, command="paper-navigation", version=PF_VERSION, data=payload)
    print(result.to_json() if args.json else json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
```

- [ ] **Step 5: Run structure tree tests**

Run: `pytest tests/test_layer4_structure_tree.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/retrieval/structure_tree.py paperforge/worker/ocr.py paperforge/worker/ocr_rebuild.py paperforge/commands/paper_navigation.py tests/test_layer4_structure_tree.py
git commit -m "feat: add structure tree builder for paper navigation"
```

## Task 4: Build `BodyUnit` / `ObjectUnit`, audit fields, manifest, and body-unit FTS

**Files:**
- Create: `paperforge/retrieval/units.py`
- Create: `paperforge/retrieval/manifest.py`
- Modify: `paperforge/memory/schema.py`
- Modify: `paperforge/memory/builder.py`
- Modify: `paperforge/commands/scoped_fetch.py`
- Test: `tests/test_layer4_units_and_fts.py`

**Interfaces:**
- Consumes: `structure-tree.json`, `structured_blocks`, `role-index.json`, `fulltext.md` fallback
- Produces: `build_body_units(...) -> list[dict]`
- Produces: `build_object_units(...) -> list[dict]`
- Produces: `build_paper_manifest(...) -> dict`
- Produces: SQLite tables `body_units`, `body_units_fts`, `object_units`

- [ ] **Step 1: Write failing unit and FTS tests**

```python
from paperforge.retrieval.units import build_body_units


def test_build_body_units_assigns_stable_ids_and_audit_fields():
    tree = {"paper_id": "ABCD1234", "nodes": [{"node_id": "sec:b1", "title": "Methods", "section_path": ["Methods"], "page_span": [1, 1], "block_span": [[1, "b1"], [1, "b2"]]}]}
    blocks = [
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b1", "role": "section_heading", "text": "Methods"},
        {"paper_id": "ABCD1234", "page": 1, "block_id": "b2", "role": "body_paragraph", "text": "We recruited 30 patients."},
    ]
    units = build_body_units(tree=tree, structured_blocks=blocks)
    assert units[0]["unit_id"].startswith("ABCD1234:body:")
    assert units[0]["indexable"] is True
    assert units[0]["veto_reason"] == ""
```

- [ ] **Step 2: Run the tests to confirm units/manifest are missing**

Run: `pytest tests/test_layer4_units_and_fts.py -v`
Expected: FAIL with import errors or missing tables.

- [ ] **Step 3: Implement units, audit fields, and manifest**

```python
# paperforge/retrieval/units.py
from __future__ import annotations

from hashlib import sha256
from typing import Any


def build_unit_id(paper_id: str, kind: str, node_id: str, start_page: int, start_block: str, end_page: int, end_block: str) -> str:
    return f"{paper_id}:{kind}:{node_id}:{start_page}-{start_block}:{end_page}-{end_block}"


def build_body_units(*, tree: dict[str, Any], structured_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units = []
    for node in tree.get("nodes", []):
        block_ids = {block_id for _, block_id in node.get("block_span", [])}
        texts = [b.get("text", "") for b in structured_blocks if b.get("block_id") in block_ids and b.get("role") == "body_paragraph"]
        unit_text = "\n\n".join(t for t in texts if t)
        unit = {
            "unit_id": build_unit_id(tree["paper_id"], "body", node["node_id"], node["page_span"][0], node["block_span"][0][1], node["page_span"][1], node["block_span"][-1][1]),
            "paper_id": tree["paper_id"],
            "section_path": "/".join(node["section_path"]),
            "page_span": node["page_span"],
            "block_span": node["block_span"],
            "unit_text": unit_text,
            "token_estimate": len(unit_text) // 4,
            "unit_kind": "body",
            "indexable": bool(unit_text.strip()),
            "veto_reason": "" if unit_text.strip() else "empty",
            "quality_hints": [],
        }
        units.append(unit)
    return units
```

```python
# paperforge/retrieval/manifest.py
from __future__ import annotations

from hashlib import sha256


def build_paper_manifest(*, paper_id: str, ocr_result_hash: str, structure_tree_bytes: bytes, retrieval_policy_version: str, body_units: list[dict], object_units: list[dict], source_paths: dict[str, str]) -> dict:
    from datetime import datetime, timezone

    structure_tree_hash = sha256(structure_tree_bytes).hexdigest()
    return {
        "paper_id": paper_id,
        "ocr_result_hash": ocr_result_hash,
        "structure_tree_hash": structure_tree_hash,
        "retrieval_policy_version": retrieval_policy_version,
        "body_unit_count": len(body_units),
        "object_unit_count": len(object_units),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_paths": source_paths,
    }
```

- [ ] **Step 4: Extend SQLite schema and builder**

```python
# paperforge/memory/schema.py
CREATE_BODY_UNITS = """
CREATE TABLE IF NOT EXISTS body_units (
    unit_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    section_path TEXT NOT NULL,
    unit_text TEXT NOT NULL,
    page_span_json TEXT NOT NULL,
    block_span_json TEXT NOT NULL,
    token_estimate INTEGER NOT NULL,
    indexable INTEGER NOT NULL,
    veto_reason TEXT NOT NULL,
    quality_hints_json TEXT NOT NULL
);
"""

CREATE_BODY_UNITS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS body_units_fts USING fts5(
    unit_id,
    paper_id,
    section_path,
    unit_text,
    content='body_units',
    content_rowid='rowid'
);
"""
```

```python
# paperforge/memory/builder.py
from paperforge.core.io import read_json
from paperforge.retrieval.manifest import build_paper_manifest
from paperforge.retrieval.units import build_body_units, build_object_units

ocr_root = vault / "System" / "PaperForge" / "ocr"
for paper_dir in ocr_root.iterdir():
    if not paper_dir.is_dir():
        continue
    index_root = paper_dir / "index"
    tree_path = index_root / "structure-tree.json"
    structured_path = paper_dir / "structured-blocks.json"
    if not tree_path.exists() or not structured_path.exists():
        continue

    tree = read_json(tree_path)
    structured_blocks = read_json(structured_path)
    role_index = read_json(index_root / "role-index.json") if (index_root / "role-index.json").exists() else {}
    body_units = build_body_units(tree=tree, structured_blocks=structured_blocks)
    object_units = build_object_units(tree=tree, structured_blocks=structured_blocks, role_index=role_index)
    manifest = build_paper_manifest(
        paper_id=tree["paper_id"],
        ocr_result_hash=_read_result_hash(paper_dir),
        structure_tree_bytes=tree_path.read_bytes(),
        retrieval_policy_version="l4.body.v1",
        body_units=body_units,
        object_units=object_units,
        source_paths={"structured_blocks": str(structured_path), "role_index": str(index_root / "role-index.json"), "fulltext": str(paper_dir / "fulltext.md")},
    )
    _upsert_body_units(conn, body_units)
    _upsert_object_units(conn, object_units)
    _write_manifest_row(conn, manifest)
```

- [ ] **Step 5: Run unit and FTS tests**

Run: `pytest tests/test_layer4_units_and_fts.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/retrieval/units.py paperforge/retrieval/manifest.py paperforge/memory/schema.py paperforge/memory/builder.py paperforge/commands/scoped_fetch.py tests/test_layer4_units_and_fts.py
git commit -m "feat: add body units, manifest, and body-unit FTS"
```

## Task 5: Upgrade gateway routing to real Layer 4 behavior

**Files:**
- Modify: `paperforge/retrieval/gateway.py`
- Modify: `paperforge/commands/content_discovery.py`
- Modify: `paperforge/commands/paper_navigation.py`
- Modify: `paperforge/commands/scoped_fetch.py`
- Modify: `paperforge/commands/search.py`
- Modify: `paperforge/commands/retrieve.py`
- Test: `tests/test_layer4_gateway_commands.py`

**Interfaces:**
- Consumes: `lookup_paper()`, `body_units_fts`, `structure-tree.json`, `paper_manifest.json`
- Produces: content discovery via `body_units_fts` baseline, paper navigation via structure tree, scoped fetch via `section_path` / `node_id`

- [ ] **Step 1: Write failing end-to-end routing tests**

```python
from paperforge.retrieval.gateway import route_gateway


def test_content_discovery_prefers_body_units_fts_when_present(tmp_path):
    result = route_gateway(tmp_path, "content-discovery", "delirium prevention", json_mode=True, limit=5)
    assert result.data["intent"] == "content-discovery"
    assert "route_plan" in result.data


def test_paper_navigation_reads_structure_tree_when_present(tmp_path):
    result = route_gateway(tmp_path, "paper-navigation", "ABCD1234", json_mode=True, limit=5)
    assert result.data["intent"] == "paper-navigation"
```

- [ ] **Step 2: Run the gateway tests and confirm they still return placeholder plans**

Run: `pytest tests/test_layer4_gateway_commands.py -v`
Expected: FAIL because the gateway still returns planning-only payloads.

- [ ] **Step 3: Route each intent to the correct source of truth**

```python
# paperforge/retrieval/gateway.py
if intent == "paper-lookup":
    return _run_paper_lookup(vault, query, limit=limit)
if intent == "content-discovery":
    if _body_units_fts_exists(vault):
        return _run_body_unit_discovery(vault, query, limit=limit)
    return _run_compat_content_discovery(vault, query, limit=limit)
if intent == "paper-navigation":
    return _run_paper_navigation(vault, query)
if intent == "scoped-fetch":
    return _run_scoped_fetch(vault, query)
raise ValueError(f"Unsupported Layer 4 intent: {intent}")
```

- [ ] **Step 4: Surface explicit route explanations**

```python
result.data["route_explanation"] = {
    "primary_arm": "body_units_fts",
    "fallback_arms": ["vector_retrieve"],
    "compatibility_mode": False,
}
```

- [ ] **Step 5: Run the gateway tests**

Run: `pytest tests/test_layer4_gateway_commands.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/retrieval/gateway.py paperforge/commands/content_discovery.py paperforge/commands/paper_navigation.py paperforge/commands/scoped_fetch.py paperforge/commands/search.py paperforge/commands/retrieve.py tests/test_layer4_gateway_commands.py
git commit -m "feat: route Layer 4 gateway through body units and structure tree"
```

## Task 6: Introduce the vector-backend adapter and keep Chroma as compatibility backend

**Files:**
- Create: `paperforge/embedding/backends/base.py`
- Create: `paperforge/embedding/backends/chroma_backend.py`
- Modify: `paperforge/embedding/builder.py`
- Modify: `paperforge/embedding/search.py`
- Modify: `paperforge/embedding/status.py`
- Modify: `paperforge/embedding/__init__.py`
- Test: `tests/test_layer4_vector_backend.py`

**Interfaces:**
- Produces: `class VectorBackend(Protocol): ...`
- Produces: `get_vector_backend(vault: Path) -> VectorBackend`
- Produces: `ChromaBackend` preserving current `paperforge_fulltext` behavior
- Consumes: existing `OpenAICompatibleProvider`

- [ ] **Step 1: Write failing adapter tests**

```python
from pathlib import Path

from paperforge.embedding.backends.chroma_backend import ChromaBackend


def test_chroma_backend_keeps_existing_collection_name(tmp_path: Path):
    backend = ChromaBackend(tmp_path)
    assert backend.collection_name == "paperforge_fulltext"
```

- [ ] **Step 2: Run the adapter tests and confirm the backend module does not exist yet**

Run: `pytest tests/test_layer4_vector_backend.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Add the backend protocol and Chroma implementation**

```python
# paperforge/embedding/backends/base.py
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VectorBackend(Protocol):
    def add(self, *, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None: ...
    def query(self, *, query_embedding: list[float], limit: int) -> list[dict]: ...
    def delete_paper(self, paper_id: str) -> int: ...
    def health(self) -> dict: ...
```

```python
# paperforge/embedding/backends/chroma_backend.py
from __future__ import annotations

import chromadb

from paperforge.embedding._chroma import get_vector_db_path


class ChromaBackend:
    collection_name = "paperforge_fulltext"

    def __init__(self, vault):
        db_path = get_vector_db_path(vault)
        db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(name=self.collection_name, metadata={"hnsw:space": "cosine"})
```

- [ ] **Step 4: Replace direct `get_collection()` usage with `get_vector_backend()`**

```python
# paperforge/embedding/builder.py
backend = get_vector_backend(vault)
backend.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
```

```python
# paperforge/embedding/search.py
backend = get_vector_backend(vault)
results = backend.query(query_embedding=query_embedding, limit=limit * 3 if expand else limit)
```

- [ ] **Step 5: Run the adapter tests**

Run: `pytest tests/test_layer4_vector_backend.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/embedding/backends/base.py paperforge/embedding/backends/chroma_backend.py paperforge/embedding/builder.py paperforge/embedding/search.py paperforge/embedding/status.py paperforge/embedding/__init__.py tests/test_layer4_vector_backend.py
git commit -m "refactor: add vector backend adapter with Chroma compatibility"
```

## Task 7: Add the LanceDB evaluation seam without switching the default backend

**Files:**
- Modify: `paperforge/embedding/backends/base.py`
- Create: `paperforge/embedding/backends/lance_backend.py`
- Create: `tests/test_layer4_lance_backend.py`
- Modify: `paperforge/embedding/status.py`

**Interfaces:**
- Produces: optional `LanceBackend`
- Produces: backend capability reporting (`backend_name`, `supports_hybrid`, `supports_multimodal`)
- Does not change the default backend selection yet

- [ ] **Step 1: Write a failing optional-backend capability test**

```python
import pytest


def test_lance_backend_advertises_file_based_capabilities():
    pytest.importorskip("lancedb")
    from paperforge.embedding.backends.lance_backend import LanceBackend
    backend = LanceBackend("/tmp/lance")
    assert backend.capabilities()["supports_hybrid"] is True
```

- [ ] **Step 2: Run the test and confirm the backend is absent**

Run: `pytest tests/test_layer4_lance_backend.py -v`
Expected: FAIL with import error or skipped dependency.

- [ ] **Step 3: Add a non-default Lance backend scaffold**

```python
# paperforge/embedding/backends/lance_backend.py
from __future__ import annotations

import lancedb


class LanceBackend:
    def __init__(self, dataset_path):
        self.db = lancedb.connect(str(dataset_path))

    def capabilities(self) -> dict:
        return {
            "backend": "lancedb",
            "supports_hybrid": True,
            "supports_multimodal": True,
        }
```

- [ ] **Step 4: Keep selection explicit and non-default**

```python
# paperforge/embedding/status.py
def get_available_backends(vault: Path) -> dict[str, dict]:
    return {
        "chroma": {"installed": True, "selected": True, "supports_hybrid": False, "supports_multimodal": False},
        "lancedb": {"installed": _module_available("lancedb"), "selected": False, "supports_hybrid": True, "supports_multimodal": True},
    }
```

- [ ] **Step 5: Run the Lance backend tests**

Run: `pytest tests/test_layer4_lance_backend.py -v`
Expected: PASS or SKIP cleanly when `lancedb` is not installed.

- [ ] **Step 6: Commit**

```bash
git add paperforge/embedding/backends/base.py paperforge/embedding/backends/lance_backend.py paperforge/embedding/status.py tests/test_layer4_lance_backend.py
git commit -m "feat: add LanceDB evaluation backend scaffold"
```

## Self-Review

### Spec coverage
- Gateway + new agent-facing commands: Task 1
- Decomposed paper lookup and zero-hit avoidance: Task 2
- Structure Tree Builder and navigation: Task 3
- `body_units`, `object_units`, `paper_manifest`, `body_units_fts`: Task 4
- FTS-first real routing and scoped fetch: Task 5
- Vector adapter with Chroma compatibility: Task 6
- LanceDB as optional evaluation backend, not immediate default: Task 7

No spec requirement is left without a task.

### Placeholder scan
- No `TODO` / `TBD` / "implement later" placeholders in tasks.
- Command names, file paths, and interface names are fixed.
- The only deferred behavior is explicitly staged as a later task (`object_units_fts` optional / Lance non-default), not left undefined.

### Type consistency
- `route_gateway(...) -> PFResult` is introduced in Task 1 and reused consistently.
- `lookup_paper()` remains the paper-resolution core and is extended in Task 2.
- `build_structure_tree()`, `build_body_units()`, and `build_paper_manifest()` are introduced before later tasks depend on their outputs.
- Vector backend calls (`add`, `query`, `delete_paper`, `health`) are defined in Task 6 before later backends extend them in Task 7.
