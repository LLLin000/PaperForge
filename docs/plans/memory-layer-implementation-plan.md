# Memory Layer 改造 — 实施计划

> 基于：`2026-07-06-memory-layer-overhaul-design.md`
> 状态：待执行
> 策略：5 个 PR 顺序执行，PR n+1 依赖 PR n

---

## 总依赖图

```
PR 1: 结构树 + body_units 正确性
  │
  ▼
PR 2: Memory Builder 增量
  │
  ▼
PR 3: Content Discovery 行为（语义依赖 PR 2，PR 2 后做）
  │
  ▼
PR 4: Embedding 双 collection（依赖 PR 1 + PR 2）
  │
  ▼
PR 5: Retrieve 合并（依赖 PR 4）
```

---

## PR 1：结构树和 body_units 正确性（最核心，不可拆分）

**目标：** 从 rendered markdown H1-H6 产出真实嵌套结构树，body_units 跟随树递归生成，不重复、不丢内容。

### 文件变更

| 操作 | 文件 | 改动 |
|------|------|------|
| 新增 | `paperforge/core/io.py` | `read_jsonl(path)` — jsonl 逐行读取（待加） |
| 修改 | `paperforge/worker/ocr_render.py` | `render_fulltext_markdown()` 新增 `return_events=False` 参数；为 True 时返回 `RenderOutput(markdown, heading_events, emitted_block_events)`。**不破坏旧返回类型。** |
| 修改 | `paperforge/worker/ocr_rebuild.py` Phase 4/5 | Phase 4 传 `return_events=True` → `RenderOutput` 传入 Phase 5 |
| 修改 | `paperforge/worker/ocr.py` Phase 6 | 同上顺序调整 |
| 新增 | render 阶段产出 | `render/render-map.json`：`{headings: [...], emitted_blocks: [...]}` |
| 重写 | `paperforge/retrieval/structure_tree.py` | `build_structure_tree(heading_events, emitted_block_events, structured_blocks)` — stack 算法，interval 基于 emitted order |
| 修改 | `paperforge/retrieval/units.py` | `build_body_units()` / `build_object_units()` recursive walk，`own_block_ids`，role helper |
| 修改 | `paperforge/memory/schema.py` | body_units 表加字段；CURRENT_SCHEMA_VERSION → 4 |

### 实现要点

#### 1.1 RenderOutput 与 render-map.json

**不直接改 `render_fulltext_markdown()` 返回类型**——当前返回 `str`，旧调用点很多。新增 `return_events=False` 参数：

```python
@dataclass
class RenderOutput:
    markdown: str
    heading_events: list[dict]         # heading block 事件
    emitted_block_events: list[dict]   # 所有真正进入正文阅读流的 block

def render_fulltext_markdown(..., return_events=False) -> str | RenderOutput:
    ...
    if return_events:
        return RenderOutput(markdown=markdown,
                            heading_events=heading_events,
                            emitted_block_events=emitted_block_events)
    return markdown
```

`heading_events` 每条记录：

```json
{"line_number": 42, "markdown_level": 3, "title": "Study population",
 "page": 2, "block_id": "b_10", "emitted_order": 7}
```

`emitted_block_events` 每条记录（每个真正进入正文阅读流的 block）：

```json
{"emitted_order": 123, "line_start": 456, "line_end": 460,
 "page": 3, "block_id": "b_10", "role": "body_paragraph",
 "emitted_as": "body"}
```

写入 `render/render-map.json`：

```json
{"headings": [...], "emitted_blocks": [...]}
```

`build_structure_tree()` **不再依赖 structured_blocks 的 `_emitted_order`**（该字段不存在），而是接收 `emitted_block_events`。

#### 1.2 Phase 4/5 顺序和数据流

```
× 当前:
  Phase 4: render_fulltext_markdown(...) → markdown (str)
  Phase 5: build_role_indexes
           build_structure_tree(structured)     ← 此时无 heading／emitted 信息
           write_render_outputs(...)

✓ 改为:
  Phase 4: rendered = render_fulltext_markdown(..., return_events=True)
           return rendered, health_overall

  Phase 5: write_render_outputs(..., markdown=rendered.markdown,
                                 heading_events=rendered.heading_events,
                                 emitted_block_events=rendered.emitted_block_events)
           build_role_indexes(...)
           build_structure_tree(
               heading_events=rendered.heading_events,
               emitted_block_events=rendered.emitted_block_events,
               structured_blocks=structured,
           )
           write_structure_tree(index/structure-tree.json)
```

两处都改：
- `paperforge/worker/ocr_rebuild.py` — rebuild 路径
- `paperforge/worker/ocr.py` — 初始 OCR 路径

`write_render_outputs()` 新增参数 `heading_events` / `emitted_block_events`，写入 `render/render-map.json`。

#### 1.3 build_structure_tree() 使用 emitted_block_events

```python
def build_structure_tree(heading_events, emitted_block_events, structured_blocks):
    # 1. heading_events 按 emitted_order 排序
    heading_events.sort(key=lambda h: h["emitted_order"])

    # 2. 建立 block_id → structured_block 的映射
    block_map = {b["block_id"]: b for b in structured_blocks}

    # 3. stack 建树
    stack, root_nodes = [], []
    for h in heading_events:
        node = {
            "node_id": f"sec:{h['block_id']}",
            "kind": "section",
            "title": h["title"],
            "level": h["markdown_level"],
            "page_span": [h["page"], h["page"]],
            "block_id": h["block_id"],
            "own_block_ids": [],
            "subtree_block_ids": [],
            "children": [],
            "objects": [],
        }
        while stack and stack[-1]["level"] >= h["markdown_level"]:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root_nodes.append(node)
        stack.append(node)

    # 4. 计算 block intervals（基于 emitted_block_events）
    _assign_block_intervals(root_nodes, heading_events, emitted_block_events)
    return {"paper_id": ..., "nodes": root_nodes}
```

#### 1.4 block interval 计算（基于 emitted order）

```python
def _assign_block_intervals(nodes, heading_events, emitted_block_events):
    # 构建每个 heading 的 emitted_order 边界
    bounds_map = {}
    for i, h in enumerate(heading_events):
        next_sibling = None
        for h2 in heading_events[i+1:]:
            if h2["markdown_level"] <= h["markdown_level"]:
                next_sibling = h2["emitted_order"]
                break
        bounds_map[h["block_id"]] = {
            "start": h["emitted_order"],
            "end": next_sibling or float("inf"),
        }

    def compute(node):
        bounds = bounds_map.get(node["block_id"])
        if not bounds:
            return
        # subtree = bounds 范围内的所有 emitted blocks
        node["subtree_block_ids"] = [
            e["block_id"] for e in emitted_block_events
            if bounds["start"] <= e["emitted_order"] < bounds["end"]
        ]
        for child in node.get("children", []):
            compute(child)
        # own = subtree − children subtree − heading blocks
        child_ids = set()
        for child in node.get("children", []):
            child_ids.update(child.get("subtree_block_ids", []))
        node["own_block_ids"] = [
            bid for bid in node["subtree_block_ids"]
            if bid not in child_ids and bid != node["block_id"]
        ]

    for n in nodes:
        compute(n)
```

#### 1.5 build_body_units() 递归

```python
def _body_unit_role_kind(role):
    if role == "body_paragraph": return "body"
    if role in {"structured_insert", "non_body_insert", "backmatter_body"}:
        return "backmatter_body"
    return None  # reference_item, reference_heading, heading, caption, asset → excluded

def build_body_units(tree, structured_blocks):
    units = []
    block_map = {b["block_id"]: b for b in structured_blocks}

    def walk(node, path):
        this_path = path + [node["title"]]
        own = [block_map[bid] for bid in node.get("own_block_ids", [])
               if bid in block_map
               and _body_unit_role_kind(block_map[bid].get("role", ""))]
        if own:
            from itertools import groupby
            for kind, grp in groupby(own, key=lambda b: _body_unit_role_kind(b["role"])):
                if not kind: continue
                text = "\n\n".join(b.get("text","") for b in grp)
                parts = _split_if_oversized(text, 1000)
                n = len(parts)
                for pi, pt in enumerate(parts):
                    ord_ = pi + 1 if n > 1 else 0
                    suf = f":part_{ord_:03d}" if ord_ else ""
                    units.append({
                        "unit_id": f"{paper_id}:body:{node['node_id']}{suf}",
                        "paper_id": paper_id,
                        "section_path": "/".join(this_path),
                        "section_path_json": json.dumps(this_path),
                        "section_level": node["level"],
                        "section_title": node["title"],
                        "page_span": node["page_span"],
                        "unit_text": pt,
                        "token_estimate": len(pt)//4,
                        "unit_kind": kind,
                        "part_ordinal": ord_,
                        "indexable": True,
                        "veto_reason": "",
                        "quality_hints": [],
                    })
        for child in node.get("children", []):
            walk(child, path)

    for root in tree.get("nodes", []):
        walk(root, [])
    return units
```

#### 1.6 build_object_units() own_block_ids

与 body_units 同理，只取 `own_block_ids` 范围内 role 为 figure/table/object 的 blocks。一个 object 只归属一个最具体的 section。

#### 1.7 schema 升级

```sql
-- CURRENT_SCHEMA_VERSION: 3 → 4
ALTER TABLE body_units ADD COLUMN section_path_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE body_units ADD COLUMN section_level INTEGER NOT NULL DEFAULT 0;
ALTER TABLE body_units ADD COLUMN section_title TEXT NOT NULL DEFAULT '';
ALTER TABLE body_units ADD COLUMN part_ordinal INTEGER NOT NULL DEFAULT 0;
```

### 测试清单

```
1. duplicate heading title 通过 block_id 区分，不通过 title match
2. H2/H3/H3 sibling 产生正确 section_path（无跨级错误）
3. parent intro + child + parent summary:
   parent.own_block_ids = [intro_para, summary_para]（不含 child 内容）
4. child body 不重复出现在 parent unit
5. empty container 不产生 body unit
6. reference_item 不进入 body_units
7. structured_insert 进入 backmatter_body unit
8. mixed body + backmatter: 拆成两个 unit，不同 unit_kind
9. token cap: >1000 tokens 拆 part_001 / part_002
10. object 只归属最具体 section
11. rendered order ≠ structured order: tree interval 基于 emitted order
12. consumed object blocks 不进入 own_block_ids
```

---

## PR 2：Memory Builder 增量

**目标：** memory build 不再被 canonical_index_hash 锁定，per-paper 检测 OCR 结果变化后增量重建 body_units。

### 文件变更

| 操作 | 文件 | 改动 |
|------|------|------|
| 修改 | `paperforge/memory/builder.py` | 结构化路径修正；不 early return；per-paper ocr_result_hash 增量；三级 fallback；schema v4 兼容 |
| 修改 | `paperforge/memory/schema.py` | ensure_schema 支持 v4 upgrade path |

### 实现要点

#### 2.1 路径修正

```python
# 改前
structured_path = ocr_dir / "structured-blocks.json"
structured_blocks = read_json(structured_path)

# 改后
structured_path = ocr_dir / "structure" / "blocks.structured.jsonl"
structured_blocks = read_jsonl(structured_path)
```

#### 2.2 不 early return

```python
# 改前
if canonical_hash matches and db_path.exists():
    return {"papers_indexed": N, "hash_match": True}

# 改后
index_changed = not _hash_matches(...)
if index_changed:
    _rebuild_metadata_tables(conn, items)    # papers / aliases / FTS
    _rebuild_all_units(conn, items, vault)   # body + object + manifest
else:
    _incremental_units_only(conn, items, vault)  # only body/object units
```

#### 2.3 _incremental_units_only()

```python
def _incremental_units_only(conn, items, vault):
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    if not ocr_root.exists():
        return
    for entry in items:
        key = entry["zotero_key"]
        paper_dir = ocr_root / key
        tree_path = paper_dir / "index" / "structure-tree.json"
        blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
        if not tree_path.exists() or not blocks_path.exists():
            continue
        current_hash = _resolve_ocr_result_hash(paper_dir)
        row = conn.execute(
            "SELECT value FROM meta WHERE key=?", (f"manifest:{key}",)
        ).fetchone()
        if row:
            stored = json.loads(row[0])
            if stored.get("ocr_result_hash") == current_hash:
                continue
        _rebuild_paper_units(conn, key, paper_dir, tree_path, blocks_path)
```

#### 2.4 _resolve_ocr_result_hash() 三级 fallback

```python
def _resolve_ocr_result_hash(paper_dir):
    # 1. index/result-hash.txt
    rp = paper_dir / "index" / "result-hash.txt"
    if rp.exists():
        return rp.read_text().strip()
    # 2. hash of structured artifacts
    h = hashlib.sha256()
    for rel in ["structure/blocks.structured.jsonl", "index/structure-tree.json",
                 "index/role-index.json"]:
        p = paper_dir / rel
        if p.exists():
            h.update(p.read_bytes())
    if h.hexdigest() != hashlib.sha256(b"").hexdigest():
        return h.hexdigest()
    # 3. meta derived_version
    meta_p = paper_dir / "meta.json"
    if meta_p.exists():
        dv = json.loads(meta_p.read_text()).get("derived_version", {})
        return hashlib.sha256(json.dumps(dv, sort_keys=True).encode()).hexdigest()
    return ""
```

#### 2.5 _rebuild_paper_units() 删除 + _upsert_body_units() 只插入

**职责分离：** `_rebuild_paper_units()` 负责 DELETE；`_upsert_body_units()` 只 INSERT + FTS。

```python
def _rebuild_paper_units(conn, key, paper_dir, tree_path, blocks_path):
    # ── 删除（一个地方做）──
    conn.execute("DELETE FROM body_units WHERE paper_id = ?", (key,))
    conn.execute("DELETE FROM body_units_fts WHERE paper_id = ?", (key,))
    conn.execute("DELETE FROM object_units WHERE paper_id = ?", (key,))

    # ── 构建 ──
    tree = json.loads(tree_path.read_text())
    blocks = read_jsonl(blocks_path)
    from paperforge.retrieval.units import build_body_units, build_object_units
    body_units = build_body_units(tree=tree, structured_blocks=blocks)
    object_units = build_object_units(tree=tree, structured_blocks=blocks, ...)

    # ── 插入 + FTS（不做 DELETE）──
    _upsert_body_units(conn, body_units)
    _upsert_object_units(conn, object_units)

    # ── manifest ──
    from paperforge.retrieval.manifest import build_paper_manifest
    manifest = build_paper_manifest(paper_id=key, ...)
    _write_manifest_row(conn, manifest)
```

`_upsert_body_units()` 只 INSERT + FTS，DELETE 已在 `_rebuild_paper_units()` 完成：

```python
def _upsert_body_units(conn, body_units):
    for unit in body_units:
        conn.execute("""INSERT INTO body_units (...) VALUES (...)""", ...)
    paper_ids = list({u["paper_id"] for u in body_units})
    for pid in paper_ids:
        conn.execute("""INSERT INTO body_units_fts(...)
                        SELECT rowid, unit_id, paper_id, section_path, unit_text
                        FROM body_units
                        WHERE paper_id = ? AND indexable = 1""", (pid,))
```

---

## PR 3：Content Discovery 行为

**目标：** body_units_fts 做 primary 检索，无结果时不静默 fallback。

**依赖：** PR 2 后做（依赖 body_units 表稳定 + indexable 语义稳定 + schema v4）。

### 文件变更

| 操作 | 文件 | 改动 |
|------|------|------|
| 修改 | `paperforge/retrieval/gateway.py` | `_run_body_unit_discovery()` 无结果时返回空 + coverage 提示 |

### 实现要点

```python
def _run_body_unit_discovery(vault, query, limit=5):
    body_rows = _search_body_units_fts(vault, query, limit)
    coverage = _get_body_coverage(conn)
    if not body_rows:
        return PFResult(ok=True, data={
            "results": [],
            "coverage": coverage,
            "next_action": {
                "command": f"paperforge search {query}",
                "reason": (f"正文检索无匹配。正文索引覆盖 "
                           f"{coverage['body_papers']}/{coverage['ocr_papers']} 篇 OCR 完成论文。"
                           f"尝试 paperforge search 进行元数据全文搜索。")
            }
        })
    return PFResult(ok=True, data={"results": body_rows, "coverage": coverage})

def _get_body_coverage(conn):
    body = conn.execute("SELECT COUNT(DISTINCT paper_id) FROM body_units WHERE indexable=1").fetchone()[0]
    ocr = conn.execute("SELECT COUNT(*) FROM papers WHERE ocr_status='done'").fetchone()[0]
    lib = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    return {"body_papers": body, "ocr_papers": ocr, "library_papers": lib}
```

---

## PR 4：Embedding 双 collection

**目标：** 新建 `paperforge_body` collection，embed builder 从 DB 读 body_units。

### 文件变更

| 操作 | 文件 | 改动 |
|------|------|------|
| 修改 | `paperforge/embedding/_chroma.py` | `get_collection()` 支持 `name` 参数；`delete_paper_vectors()` 双删 |
| 修改 | `paperforge/embedding/builder.py` | 新增 `embed_body_units()`；`get_body_units_for_embedding()` 读 DB |
| 修改 | `paperforge/embedding/search.py` | 新增 `merge_retrieve()` |
| 修改 | `paperforge/embedding/status.py` | 统计两个 collection |
| 修改 | `paperforge/commands/embed.py` | build 流程以 DB 分流、resume 检测 body_units_hash |

### 实现要点

#### 4.1 get_collection(name=)

```python
def get_collection(vault, name="paperforge_fulltext"):
    db_path = get_vector_db_path(vault)
    client = chromadb.PersistentClient(str(db_path))
    return client.get_or_create_collection(
        name=name, metadata={"hnsw:space": "cosine"},
    )
```

#### 4.2 embed build 分流（以 DB 为准）

是否走 body_units 路径以 DB `body_units` 表为准（Memory Builder 是唯一生产者），不重复检测文件。

```python
def _has_body_units_in_db(vault, key) -> bool:
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return False
    conn = get_connection(db_path, read_only=True)
    cnt = conn.execute(
        "SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1",
        (key,)
    ).fetchone()[0]
    conn.close()
    return cnt > 0

for entry in papers:
    key = entry["zotero_key"]
    has_body = _has_body_units_in_db(vault, key)

    if has_body:
        body_units = get_body_units_for_embedding(vault, key)
        if not body_units:
            continue
        if resume:
            col = get_collection(vault, name="paperforge_body")
            # Chroma: 不依赖多字段 where 隐式 AND
            existing = col.get(where={"paper_id": key}, limit=1)
            metas = existing.get("metadatas", [])
            if metas and metas[0].get("body_units_hash") == current_hash:
                papers_skipped += 1; continue
        delete_paper_vectors(vault, key)
        embed_body_units(vault, key, body_units)
    else:
        # 文件存在但 DB 无 body_units → 提示先 memory build
        ocr_root = vault / "System" / "PaperForge" / "ocr" / key
        has_files = ((ocr_root / "structure" / "blocks.structured.jsonl").exists()
                     and (ocr_root / "index" / "structure-tree.json").exists())
        if has_files:
            print(f"Skip {key}: has structured blocks but no body_units in DB. "
                  f"Run `paperforge memory build` first.")
            continue
        # 旧路径
        fulltext_path = vault / (entry.get("fulltext_path") or "")
        if resume:
            col = get_collection(vault, name="paperforge_fulltext")
            existing = col.get(where={"paper_id": key}, limit=1)
            if existing.get("ids"):
                papers_skipped += 1; continue
        delete_paper_vectors(vault, key)
        chunks = chunk_fulltext(fulltext_path)
        if chunks:
            embed_paper(vault, key, chunks)
```

---

## PR 5：Retrieve 合并

**目标：** 同时查两个 collection，unit-level 去重，per-paper cap。

### 文件变更

| 操作 | 文件 | 改动 |
|------|------|------|
| 新增 | `paperforge/embedding/search.py` | `merge_retrieve()` |
| 修改 | `paperforge/commands/retrieve.py` | 调 `merge_retrieve()` 替代 `retrieve_chunks()` |

### 实现要点

```python
RETRIEVAL_COLLECTIONS = ["paperforge_fulltext", "paperforge_body"]

def merge_retrieve(vault, query, limit=5, expand=True):
    provider = OpenAICompatibleProvider(vault)
    q_emb = provider.encode_single(query)
    n = limit * 2

    all_results = []
    for name in RETRIEVAL_COLLECTIONS:
        try:
            col = get_collection(vault, name=name)
            res = col.query(
                query_embeddings=[q_emb],
                n_results=n,
                include=["documents", "metadatas", "distances"],
            )
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                all_results.append({
                    "paper_id": meta.get("paper_id", ""),
                    "section_path": meta.get("section_path", ""),
                    "chunk_text": doc,
                    "score": round(1.0 - dist, 4),
                    "source": "legacy_chunk" if name == "paperforge_fulltext" else "body_unit",
                    "unit_id": meta.get("chunk_index", ""),
                })
        except Exception:
            continue

    # 排序 + unit-level 去重 + per-paper cap
    all_results.sort(key=lambda r: r["score"], reverse=True)
    seen = set()
    per_paper = {}
    merged = []
    for r in all_results:
        # dedupe key: (source, unit_id) 或 (source, paper_id+text_hash) 防空 unit_id
        dedupe_key = (r["source"], r["unit_id"]) if r.get("unit_id") else (
            r["source"], r["paper_id"], hash(r["chunk_text"])
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        pid = r["paper_id"]
        if per_paper.get(pid, 0) >= 2:
            continue
        per_paper[pid] = per_paper.get(pid, 0) + 1
        merged.append(r)
        if len(merged) >= limit:
            break
    return merged
```

---

## 执行顺序

```
Step 1: PR 1（最核心，不可拆）
  → 验证: body_units 表有行，section_path 正确
  → 验证: rendered order ≠ structured order 时边界正确

Step 2: PR 2
  → 验证: rebuild 后 memory build 增量更新 body_units
  → 验证: content-discovery 返回正文结果

Step 3: PR 3（依赖 PR 2）
  → 验证: content-discovery 无结果时返回空 + coverage 提示

Step 4: PR 4
  → 验证: embed build 写入 paperforge_body
  → 验证: resume 正确跳过已嵌入的论文（通过 body_units_hash）

Step 5: PR 5
  → 验证: retrieve 返回合并结果，unit-level 去重 + per-paper cap
```
