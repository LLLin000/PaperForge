# Memory Layer — Functional Test Plan

> 目标：验证 memory layer 改造（PR 1-6）在真实 vault 上端到端正确性
>
> 测试分两层：
> - **Layer A**（artifact consistency）：无外部 API 依赖，1–2 分钟
> - **Layer B**（vector/API）：需要 embedding API key，5–10 分钟

---

## 目录

1. [Layer A 自动脚本](#layer-a-自动脚本)
2. [Render Events](#1-render-events)
3. [Structure Tree](#2-structure-tree)
4. [Body Units](#3-body-units)
5. [Object Units](#4-object-units)
6. [FTS No Duplicate](#5-fts-no-duplicate)
7. [Content Discovery](#6-content-discovery)
8. [Memory Builder Incremental](#7-memory-builder-incremental)
9. [Embed Build（Layer B）](#8-embed-build-layer-b)
10. [Retrieve Merge（Layer B）](#9-retrieve-merge-layer-b)
11. [Backmatter & Abstract 专项](#10-backmatter--abstract-专项)
12. [Regression](#11-regression)

---

## Layer A 自动脚本

```python
"""Layer A: artifact consistency tests. No API calls, 1-2 min."""

import sys, json, sqlite3
from pathlib import Path
from collections import Counter
from paperforge.core.io import read_json, read_jsonl
from paperforge.worker.ocr_index import build_role_indexes
from paperforge.retrieval.structure_tree import build_structure_tree
from paperforge.retrieval.units import build_body_units, build_object_units
from paperforge.memory.builder import _upsert_body_units
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.manifest import (
    compute_body_units_hash, RETRIEVAL_POLICY_VERSION,
)

VAULT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("D:/L/OB/Literature-hub")
OCR_ROOT = VAULT / "System" / "PaperForge" / "ocr"
# Use persisted rebuild papers (have structure-tree + render-map)
KEYS = sorted(
    d.name for d in OCR_ROOT.iterdir()
    if d.is_dir()
    and (d / "index" / "structure-tree.json").exists()
    and (d / "render" / "render-map.json").exists()
)[:10]

pass_count = 0
fail_count = 0

def check(name, cond, detail=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
    else:
        fail_count += 1
        print(f"  ❌ {name} — {detail}")

def all_nodes(tree):
    """Walk tree and yield all nodes."""
    def _walk(nodes):
        for n in nodes:
            yield n
            yield from _walk(n.get("children", []))
    return list(_walk(tree.get("nodes", [])))


# ════════════════════════════════════════════════════════════════════════
# 1. Render Events (from persisted render-map.json)
# ════════════════════════════════════════════════════════════════════════
print("\n=== 1. Render Events ===")
for key in KEYS:
    try:
        render_map = read_json(OCR_ROOT / key / "render" / "render-map.json")
        heading_events = render_map.get("headings", [])
        emitted_events = render_map.get("emitted_blocks", [])
        check(f"{key}: render-map.json exists", True)
        check(f"{key}: heading_events is list", isinstance(heading_events, list))
        check(f"{key}: emitted_block_events is list", isinstance(emitted_events, list))

        # Monotonic + unique emitted_order (NOT consecutive — other blocks interleave)
        h_orders = [h["emitted_order"] for h in heading_events]
        e_orders = [e["emitted_order"] for e in emitted_events]
        check(f"{key}: heading orders ascending", h_orders == sorted(h_orders))
        check(f"{key}: emitted orders ascending", e_orders == sorted(e_orders))
        check(f"{key}: heading orders unique", len(set(h_orders)) == len(h_orders))
        check(f"{key}: emitted orders unique", len(set(e_orders)) == len(e_orders))

        # Each heading can be found as section start in emitted events
        for h in heading_events[:1]:  # check first heading only for speed
            matching = [e for e in emitted_events if e["emitted_order"] == h["emitted_order"]]
            check(f"{key}: heading has matching emitted block", len(matching) >= 1)
    except Exception as e:
        check(f"{key}: no crash", False, str(e))

# ════════════════════════════════════════════════════════════════════════
# 2. Structure Tree (from persisted structure-tree.json)
# ════════════════════════════════════════════════════════════════════════
print("\n=== 2. Structure Tree ===")
for key in KEYS:
    try:
        tree = read_json(OCR_ROOT / key / "index" / "structure-tree.json")
        nodes = all_nodes(tree)
        render_map = read_json(OCR_ROOT / key / "render" / "render-map.json")
        emitted_ids = {str(e["block_id"]) for e in render_map["emitted_blocks"] if e.get("block_id")}

        check(f"{key}: tree has nodes", len(nodes) > 0)

        # Nesting correctness
        depth_ok = all(
            c["level"] > p["level"]
            for p in nodes for c in p.get("children", [])
        )
        check(f"{key}: nesting correct (child level > parent)", depth_ok)

        # Unique node_ids
        nids = [n["node_id"] for n in nodes]
        check(f"{key}: unique node_ids", len(set(nids)) == len(nids))

        # own_block_ids ⊆ emitted_ids
        own_ok = all(
            set(n.get("own_block_ids", [])).issubset(emitted_ids)
            for n in nodes
        )
        check(f"{key}: own_block_ids in emitted blocks", own_ok)

        # subtree_block_ids ⊆ emitted_ids
        sub_ok = all(
            set(n.get("subtree_block_ids", [])).issubset(emitted_ids)
            for n in nodes
        )
        check(f"{key}: subtree_block_ids in emitted blocks", sub_ok)

        # own does not overlap children's subtree
        overlap = False
        for n in nodes:
            child_sub = set()
            for c in n.get("children", []):
                child_sub.update(c.get("subtree_block_ids", []))
            own_set = set(n.get("own_block_ids", []))
            if own_set & child_sub:
                overlap = True
        check(f"{key}: own vs child no overlap", not overlap)

        # page_span consistency
        for n in nodes:
            pages = [
                e["page"] for e in render_map["emitted_blocks"]
                if str(e.get("block_id")) in set(n.get("subtree_block_ids", []))
                and e.get("page") is not None
            ]
            if pages:
                span = n.get("page_span", [])
                check(f"{key}: page_span[{n['node_id']}] min",
                      span[0] <= min(pages))
                check(f"{key}: page_span[{n['node_id']}] max",
                      span[1] >= max(pages))
    except Exception as e:
        check(f"{key}: no crash", False, str(e))

# ════════════════════════════════════════════════════════════════════════
# 3. Body Units (read from DB, rebuild from persisted files)
# ════════════════════════════════════════════════════════════════════════
print("\n=== 3. Body Units ===")
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
ensure_schema(conn)

all_unit_ids = []
for key in KEYS:
    try:
        blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
        tree = read_json(OCR_ROOT / key / "index" / "structure-tree.json")
        role_index = read_json(OCR_ROOT / key / "index" / "role-index.json")
        units = build_body_units(tree=tree, structured_blocks=blocks)

        ids = [u["unit_id"] for u in units]
        all_unit_ids.extend(ids)

        check(f"{key}: unit_ids unique", len(set(ids)) == len(ids))

        for u in units:
            # Token cap: recursive split guarantees len//4 <= 1000
            check(f"{key}: token cap {u['unit_id'][:30]}",
                  len(u["unit_text"]) // 4 <= 1000,
                  f"{len(u['unit_text'])//4} tokens")

            # section_path integrity
            check(f"{key}: section_path matches json",
                  u["section_path"] == "/".join(json.loads(u["section_path_json"])))

            # part_ordinal logic
            if u["part_ordinal"]:
                check(f"{key}: part_ordinal in id",
                      f":part_{u['part_ordinal']:03d}" in u["unit_id"])

        # Role filtering
        for b in blocks:
            role = b.get("role", "")
            if role in ("reference_item", "reference_heading"):
                bid_text = b.get("text", "")
                for u in units:
                    if bid_text and bid_text in u["unit_text"]:
                        check(f"{key}: ref excluded", False,
                              f"reference_item text found in body unit: {bid_text[:40]}")

    except Exception as e:
        check(f"{key}: no crash", False, str(e))

# ════════════════════════════════════════════════════════════════════════
# 4. Object Units (from real role_index)
# ════════════════════════════════════════════════════════════════════════
print("\n=== 4. Object Units ===")
for key in KEYS:
    try:
        blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
        tree = read_json(OCR_ROOT / key / "index" / "structure-tree.json")
        role_index = read_json(OCR_ROOT / key / "index" / "role-index.json")
        object_units = build_object_units(
            tree=tree, structured_blocks=blocks, role_index=role_index,
        )

        for ou in object_units:
            check(f"{key}: obj kind valid",
                  ou["object_kind"] in {"figure", "table"})
            check(f"{key}: obj caption not empty",
                  bool(ou["caption_text"].strip()))
            check(f"{key}: obj section_path not empty",
                  bool(ou["section_path"].strip()))

        print(f"  {key}: {len(object_units)} object units")

        # Verify both key formats work
        role_index_a = {"captions": [{"figure_id": "FigT", "text": "Test fig"}]}
        role_index_b = {"figure_captions": [{"figure_id": "FigT", "text": "Test fig"}]}
        empty_tree = {"paper_id": "T", "nodes": [
            {"node_id": "sec:0", "title": "T", "level": 1, "block_id": 0,
             "own_block_ids": [], "subtree_block_ids": [], "children": [],
             "objects": [], "page_span": [1, 1]},
        ]}
        ua = build_object_units(tree=empty_tree, structured_blocks=[], role_index=role_index_a)
        ub = build_object_units(tree=empty_tree, structured_blocks=[], role_index=role_index_b)
        check(f"{key}: key compat (captions)", len(ua) == 1)
        check(f"{key}: key compat (figure_captions)", len(ub) == 1)

    except Exception as e:
        check(f"{key}: no crash", False, str(e))

# ════════════════════════════════════════════════════════════════════════
# 5. FTS No Duplicate
# ════════════════════════════════════════════════════════════════════════
print("\n=== 5. FTS No Duplicate ===")
# Upsert all 10 papers sequentially
for key in KEYS:
    blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
    tree = read_json(OCR_ROOT / key / "index" / "structure-tree.json")
    body_units = build_body_units(tree=tree, structured_blocks=blocks)
    _upsert_body_units(conn, body_units)
    conn.commit()

total_fts = conn.execute("SELECT COUNT(*) FROM body_units_fts").fetchone()[0]
total_body = conn.execute(
    "SELECT COALESCE(SUM(cnt), 0) FROM (SELECT COUNT(*) as cnt FROM body_units WHERE indexable=1 GROUP BY paper_id)"
).fetchone()[0]
check("FTS: total matches body", total_fts == total_body,
      f"FTS={total_fts} body={total_body}")

for key in KEYS:
    fts_cnt = conn.execute("SELECT COUNT(*) FROM body_units_fts WHERE paper_id=?", (key,)).fetchone()[0]
    body_cnt = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1", (key,)).fetchone()[0]
    check(f"FTS: {key} matches", fts_cnt == body_cnt,
          f"FTS={fts_cnt} body={body_cnt}")

# Re-upsert first paper, check no accumulation
key0 = KEYS[0]
blocks = read_jsonl(OCR_ROOT / key0 / "structure" / "blocks.structured.jsonl")
tree = read_json(OCR_ROOT / key0 / "index" / "structure-tree.json")
_upsert_body_units(conn, build_body_units(tree=tree, structured_blocks=blocks))
conn.commit()
fts_after = conn.execute("SELECT COUNT(*) FROM body_units_fts WHERE paper_id=?", (key0,)).fetchone()[0]
body_after = conn.execute("SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1", (key0,)).fetchone()[0]
check(f"FTS: {key0} re-upsert no accumulation", fts_after == body_after)

# ════════════════════════════════════════════════════════════════════════
# 6. Backmatter section_path check
# ════════════════════════════════════════════════════════════════════════
print("\n=== 6. Backmatter section_path ===")
backmatter_keywords = ["funding", "availability", "acknowledg",
                        "author contribution", "conflict", "ethics",
                        "competing", "supplementary", "data"]
for key in KEYS:
    blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
    tree = read_json(OCR_ROOT / key / "index" / "structure-tree.json")
    units = build_body_units(tree=tree, structured_blocks=blocks)
    for u in units:
        if u["unit_kind"] == "backmatter_body":
            path = u["section_path"].lower()
            matched = any(k in path for k in backmatter_keywords)
            last_section = path.split("/")[-1]
            if not matched:
                print(f"  ⚠️  backmatter_body section_path may be wrong: "
                      f"\"{u['section_path']}\" ({key})")
            check(f"backmatter: {key} \"{last_section[:30]}\"",
                  matched, f"path={u['section_path']}")

# ════════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"Layer A: {pass_count} passed, {fail_count} failed")
print(f"{'='*60}")
conn.close()
sys.exit(1 if fail_count else 0)
```

---

## 1. Render Events

**Goal:** 从持久化 `render/render-map.json` 验证 heading_events 和 emitted_block_events。

### TC-1.1: heading_events 数量合理
- 10 篇论文 heading_events >= 1
- emitted_block_events 数量 > heading_events

### TC-1.2: emitted_order 全局递增且唯一（允许跳号）
```python
h_orders == sorted(h_orders)        # monotonic
e_orders == sorted(e_orders)        # monotonic
len(set(h_orders)) == len(h_orders) # unique
len(set(e_orders)) == len(e_orders) # unique
```
- 不要求相邻 heading 连续（emitted_order 是全局事件序号，中间可能有正文 block、structured_insert 等）

### TC-1.3: 向下兼容
```python
r = render_fulltext_markdown(...)  # 默认 return_events=False
assert isinstance(r, str)
```

---

## 2. Structure Tree

**Goal:** 从持久化 `index/structure-tree.json` 验证嵌套和边界正确性。

### TC-2.1: 嵌套深度正确
- 父节点 `children` 中 node 的 `level >` 父 `level`

### TC-2.2: own_block_ids ⊆ emitted_ids
```python
emitted_ids = {str(e["block_id"]) for e in render_map["emitted_blocks"]}
for node in all_nodes:
    assert set(node["own_block_ids"]).issubset(emitted_ids)
```

### TC-2.3: subtree_block_ids 同理
- subtree 中所有 block_id 在 emitted_blocks 中存在

### TC-2.4: own_block_ids 不 overlap children 的 subtree
```python
child_sub = set()
for c in node["children"]:
    child_sub.update(c["subtree_block_ids"])
assert set(node["own_block_ids"]) & child_sub == set()
```

### TC-2.5: 重复 block_id 不产生重复 node_id
- 所有 node_id 唯一

### TC-2.6: page_span 与 emitted blocks page 一致
- span[0] <= min page in subtree
- span[1] >= max page in subtree

---

## 3. Body Units

**Goal:** `build_body_units` 产出正确的检索单元。

### TC-3.1: unit_id 全局唯一
- 10 篇论文，全部通过

### TC-3.2: unit_kind 分类正确
- `body_paragraph` → `"body"`
- `structured_insert` / `non_body_insert` / `backmatter_body` → `"backmatter_body"`
- `reference_item` / `reference_heading` → 不进入 body_units

### TC-3.3: section_path 完整性
```python
u["section_path"] == "/".join(json.loads(u["section_path_json"]))
```

### TC-3.4: token cap 硬保证
- 递归拆分后每 part `len(text) // 4 <= 1000`
- `_split_if_oversized` 使用 `_halve_text` 递归拆分直至全部达标

### TC-3.5: 空 section 不产出 body unit
- own_block_ids 为空的 node → 无 unit

### TC-3.6: Mixed body + backmatter 拆分成独立 unit
- 两个 unit_id 不同（含 `:backmatter_body` 后缀）

---

## 4. Object Units

**Goal:** `build_object_units` 从真实 `build_role_indexes` 产出。

### TC-4.1: 真实 role_index 能产出
```python
role_index = read_json(OCR_ROOT / key / "index" / "role-index.json")
object_units = build_object_units(tree=tree, structured_blocks=blocks, role_index=role_index)
for ou in object_units:
    assert ou["object_kind"] in {"figure", "table"}
    assert ou["caption_text"].strip()
    assert ou["section_path"].strip()
```

### TC-4.2: role_index key 兼容（captions 和 figure_captions 都行）
```python
build_object_units(..., role_index={"captions": [...]})          # OK
build_object_units(..., role_index={"figure_captions": [...]})   # OK
```

### TC-4.3: Object 归属 section 合理（人工 spot check 1 篇）
- Figure 1 的 section_path 接近 caption 所在 section
- Table 1 的 section_path 不是 References

---

## 5. FTS No Duplicate

**Goal:** 顺序 upsert 多篇论文后 FTS 不重复。

### TC-5.1: 顺序 upsert N 篇
```python
for key in [key_a, key_b, key_c, ...]:
    _upsert_body_units(conn, body_units)
total_fts == total_body(indexable=1)  # 严格相等
for key in keys:
    fts_per_paper == body_per_paper
```

### TC-5.2: 同一篇论文重复 upsert 不累积
- upsert → 记 N → 再 upsert → 仍为 N

### TC-5.3: 全库重建循环
- 10 篇顺序 upsert，每步后 FTS 总数 = 累计 indexable 行数

---

## 6. Content Discovery

**Goal:** 无结果时不 fallback 到 metadata。

### TC-6.1: 正文查询返回结果
- 从 DB 随机取一个 body unit 的高频短语做查询
```python
row = conn.execute("SELECT unit_text FROM body_units WHERE indexable=1 AND length(unit_text) > 200 LIMIT 1")
query = pick_meaningful_phrase(row["unit_text"])
```

### TC-6.2: 无匹配时返回 coverage
- results 为空
- coverage 存在（body_papers, ocr_papers, library_papers）
- next_action.command = "paperforge search ..."

### TC-6.3: 不静默 fallback 到 metadata
- 作者名等只在 metadata 中出现的词 → content-discovery 返回空

### TC-6.4: DB 不存在时返回错误
- ok=False, error = database_not_found

---

## 7. Memory Builder Incremental

**Goal:** `build_from_index` 增量检测 OCR hash + policy version。

### TC-7.1: Full rebuild 产出 body_units
- body_units 表 > 0 行
- FTS 行数 = indexable body_units 行数

### TC-7.2: 增量后数据不变
```bash
paperforge memory build  # 再次运行
```
- body_units 行数不变
- FTS 行数不变

### TC-7.3: OCR rebuild 触发增量
1. 选一篇已 build 的 paper
2. 修改 `index/result-hash.txt`（模拟 rebuild）
3. `paperforge memory build`
4. 该 paper body_units 刷新

### TC-7.4: 空 vault 不崩溃
- 无 OCR 目录，`paperforge memory build` 不抛异常

### TC-7.5: retrieval_policy_version 变化触发 rebuild
1. 修改 manifest 中 `retrieval_policy_version` 为旧值（如 `"l4.body.v0"`）
2. `paperforge memory build`
3. 该 paper units 重建，manifest 更新到当前 `RETRIEVAL_POLICY_VERSION`

---

## 8. Embed Build（Layer B）

**Goal:** embed build 正确路由到 body_units 或 legacy fulltext。

### TC-8.1: body_units 路径嵌入
```bash
paperforge embed build --resume
```
- body_chunk_count > 0
- paperforge_body collection metadata 含 `body_units_hash` + `retrieval_policy_version`

### TC-8.2: Legacy 路径兼容
- 未 rebuild 的论文仍走 fulltext chunk 路径
- 两个 collection 不冲突

### TC-8.3: Resume 按 body_units_hash 刷新
**流程（不是直接修改 structured blocks）：**
1. 首次 `embed build --resume` → 嵌入 N 篇
2. 再次 `--resume` → 跳过 N 篇（hash 未变）
3. `paperforge memory build`（模拟 rebuild 后 DB 更新）
4. 再次 `--resume` → 该 paper 重新嵌入

### TC-8.4: 无 body_units 但有 structured files 时提示
```
Skip <KEY>: has structured blocks but no body_units in DB.
```

### TC-8.5: 双 collection 状态
- status 输出包含 `chunk_count`, `body_chunk_count`, `total_chunks`

---

## 9. Retrieve Merge（Layer B）

**Goal:** 同时查两个 collection，去重 + per-paper cap。

### TC-9.1: 合并结果
- 返回 chunks 包含 `source: "body_unit"` 和 `source: "legacy_chunk"`
- 按 score 降序排序

### TC-9.2: 去重
- 同一 `(source, unit_id)` 不去重（不跨 source 去重文本）
- 同一 paper 最多 2 条（per-paper cap）

### TC-9.3: Per-paper cap
- 同一篇 paper 在 results 中出现 ≤ 2 次

### TC-9.4: 空结果处理
- 返回空的 chunks
- 附带 diagnostic + next_action

### TC-9.5: 向量库空时提示
- 未执行 embed build 时，ok=False，error 明确说明

---

## 10. Backmatter & Abstract 专项

### TC-10.1: backmatter_body section_path 检查
```python
for u in body_units:
    if u["unit_kind"] == "backmatter_body":
        path = u["section_path"].lower()
        assert any(k in path for k in [
            "funding", "availability", "acknowledg", "author contribution",
            "conflict", "ethics", "competing", "supplementary", "data",
        ]), f"backmatter_body may hang under wrong section: {u['section_path']}"
```

### TC-10.2: Abstract 覆盖决策
当前 abstract 不进入 heading_events → 不进 structure tree → 不进 body_units。

**决策：** Abstract 由 `paper_fts` metadata 搜索覆盖，不进入 body_units。
- TC-10.2a: `content-discovery` 搜 abstract 内容可能无结果
- TC-10.2b: `paperforge search`（metadata）应能搜到 abstract
- TC-10.2c: 如果未来需要 abstract 进 body_units，需在 renderer 中为 abstract 生成 synthetic heading_event

---

## 11. Regression

### TC-11.1: 已有单元测试全部通过
```bash
python -m pytest tests/unit/memory/ tests/test_layer4_* tests/test_ocr_render.py tests/test_ocr_rebuild.py tests/integration/test_memory_workflow.py --no-header -q
```

### TC-11.2: 不破坏旧 CLI 命令
```bash
paperforge --help
paperforge status
paperforge search "PEMF"
paperforge embed status
```

### TC-11.3: 跨 vault 切换
```bash
paperforge --vault VAULT_A embed status
paperforge --vault VAULT_B embed status
```
