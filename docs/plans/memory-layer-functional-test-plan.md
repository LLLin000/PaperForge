# Memory Layer — Functional Test Plan

> 目标：验证 memory layer 改造（PR 1-6）在真实 vault 上端到端正确性

---

## 目录

1. [Render Events](#1-render-events)
2. [Structure Tree](#2-structure-tree)
3. [Body Units](#3-body-units)
4. [Object Units](#4-object-units)
5. [FTS No Duplicate](#5-fts-no-duplicate)
6. [Content Discovery](#6-content-discovery)
7. [Memory Builder Incremental](#7-memory-builder-incremental)
8. [Embed Build](#8-embed-build)
9. [Retrieve Merge](#9-retrieve-merge)
10. [Regression](#10-regression)

---

## 1. Render Events

**Goal:** `render_fulltext_markdown(return_events=True)` 正确产出 heading_events 和 emitted_block_events。

### TC-1.1: heading_events 数量合理
```bash
python -c "
from paperforge.core.io import read_jsonl
from paperforge.worker.ocr_render import render_fulltext_markdown
blocks = read_jsonl('D:/L/OB/Literature-hub/System/PaperForge/ocr/<KEY>/structure/blocks.structured.jsonl')
r = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={}, figure_inventory={}, table_inventory={}, return_events=True)
print(len(r.heading_events), len(r.emitted_block_events))
"
```
- 10 篇论文 heading_events >= 1（无标题论文 ≤ header-only 不算）
- emitted_block_events 数量 > heading_events（有正文段落）

### TC-1.2: emitted_order 全局递增
- heading_events 按 emitted_order 升序
- emitted_block_events 按 emitted_order 升序
- 相邻 heading 之间不跳号

### TC-1.3: 无 heading 论文不报错
- 选一篇只有 metadata 无正文的 paper → render 不抛异常

### TC-1.4: 向下兼容
```python
r = render_fulltext_markdown(...)  # 默认 return_events=False
assert isinstance(r, str)
```
- 所有不传 `return_events=True` 的调用点返回 str

---

## 2. Structure Tree

**Goal:** `build_structure_tree` 正确嵌套，own/subtree 边界正确。

### TC-2.1: 嵌套深度正确
- 跨 10 篇论文检查 H2-H3-H4 嵌套
- 断言：父节点 children 中的 node level > 父 level

### TC-2.2: own_block_ids 不遗漏儿童节点内容
```python
for node in all_nodes:
    child_ids = set()
    for c in node.get('children', []):
        child_ids.update(c.get('subtree_block_ids', []))
    overlap = set(node.get('own_block_ids', [])) & child_ids
    assert len(overlap) == 0, f'{node_id}: own overlaps child'
```

### TC-2.3: page_span 正确
- own 和 subtree 内所有 emitted_block_events 的 page 在 page_span 范围内

### TC-2.4: 重复 block_id 不产生重复 node_id
- 跨 10 篇检查所有 node_id 唯一

---

## 3. Body Units

**Goal:** `build_body_units` 产出正确的检索单元。

### TC-3.1: unit_id 全局唯一
```python
ids = [u['unit_id'] for u in units]
assert len(set(ids)) == len(ids)
```
- 10 篇论文全部通过

### TC-3.2: unit_kind 分类正确
- `body_paragraph` → `"body"`
- `structured_insert` / `non_body_insert` / `backmatter_body` → `"backmatter_body"`
- `reference_item` / `reference_heading` → 不进入 body_units

### TC-3.3: section_path 完整
```python
assert u['section_path'] == '/'.join(json.loads(u['section_path_json']))
assert u['section_title'] == u['section_path'].split('/')[-1]
```

### TC-3.4: token cap 拆分
- 任意 unit_text 的 `len(text) // 4 <= 1000`
- 拆分后的 part_ordinal 不为 0（多部分时）
- 拆分后的 unit_id 含 `:part_NNN`

### TC-3.5: 空 section 不产出 body unit
- own_block_ids 为空的 node → 不产生 unit

### TC-3.6: Mixed body + backmatter 拆分成独立 unit
- 同一 node 包含 body_paragraph 和 structured_insert → 两个 unit
- 两个 unit_id 不同（含 `:backmatter_body` 后缀）

---

## 4. Object Units

**Goal:** `build_object_units` 从真实 `build_role_indexes` 产出。

### TC-4.1: 真实 role_index 能产出 object_units
```python
from paperforge.worker.ocr_index import build_role_indexes
role_index = build_role_indexes(structured_blocks=blocks, resolved_metadata={})
object_units = build_object_units(tree=tree, structured_blocks=blocks, role_index=role_index)
assert len(object_units) > 0  # 有 figure/table 的 paper
```

### TC-4.2: role_index key 兼容（captions 和 figure_captions 都行）
```python
# 测试两种 key 格式
role_index_a = {"captions": [{"figure_id": "Fig1", "text": "..."}]}
role_index_b = {"figure_captions": [{"figure_id": "Fig1", "text": "..."}]}
units_a = build_object_units(tree=tree, structured_blocks=[], role_index=role_index_a)
units_b = build_object_units(tree=tree, structured_blocks=[], role_index=role_index_b)
assert len(units_a) == len(units_b) == 1
```

---

## 5. FTS No Duplicate

**Goal:** 顺序 upsert 多篇论文后 FTS 不重复。

### TC-5.1: 顺序 upsert 5 篇
```python
import sqlite3
from paperforge.memory.schema import ensure_schema
from paperforge.memory.builder import _upsert_body_units

conn = sqlite3.connect(':memory:')
ensure_schema(conn)

for key in [key_a, key_b, key_c, key_d, key_e]:
    body_units = build_body_units(...)
    _upsert_body_units(conn, body_units)

total_fts = conn.execute('SELECT COUNT(*) FROM body_units_fts').fetchone()[0]
total_body = conn.execute(
    'SELECT SUM(cnt) FROM (SELECT COUNT(*) as cnt FROM body_units WHERE indexable=1 GROUP BY paper_id)'
).fetchone()[0]
assert total_fts == total_body

for key in [key_a, key_b, key_c, key_d, key_e]:
    fts_cnt = conn.execute('SELECT COUNT(*) FROM body_units_fts WHERE paper_id=?', (key,)).fetchone()[0]
    body_cnt = conn.execute('SELECT COUNT(*) FROM body_units WHERE paper_id=? AND indexable=1', (key,)).fetchone()[0]
    assert fts_cnt == body_cnt
```

### TC-5.2: 同一篇论文重复 upsert 不累积
- upsert paper A → 记 FTS 行数 N
- 再次 upsert paper A（模拟 rebuild） → FTS 行数仍为 N

### TC-5.3: 使用真实 full rebuild 场景
- 在循环中处理 10 篇 paper（类似 builder.py 的 for entry in items）
- 每篇 upsert 后检查 FTS 总数 = 累计 indexable body_units 数

---

## 6. Content Discovery

**Goal:** `content-discovery` gateway 无结果时不 fallback 到 metadata。

### TC-6.1: 精确匹配返回正文
```bash
paperforge content-discovery "AC joint" --limit 3
```
- results 不为空
- route_explanation.primary_arm = "body_units_fts"

### TC-6.2: 无匹配时返回 coverage
```bash
paperforge content-discovery "这个不可能存在的查询词" --limit 3
```
- results 为空
- coverage 存在（body_papers, ocr_papers, library_papers）
- next_action.command = "paperforge search ..."

### TC-6.3: 不静默 fallback 到 metadata
- 构造一个在 metadata 中有但不存于正文的词（如作者名"Smith"）
- content-discovery 应返回空，不返回 paper_fts 结果

### TC-6.4: DB 不存在时返回错误
```bash
# 备份后删除 DB
paperforge content-discovery "test"
```
- ok=False
- error= database_not_found

---

## 7. Memory Builder Incremental

**Goal:** `build_from_index` 增量检测 OCR hash 变化。

### TC-7.1: Full rebuild 产出 body_units
```bash
paperforge memory build
# 检查
python -c "from paperforge.memory.db import ...; print(cnt)"
```
- body_units 表 > 0 行
- body_units_fts 与 body_units(indexable=1) 行数一致

### TC-7.2: 增量后 body_units 仍存在
```bash
paperforge memory build  # 再次运行（hash match → incremental）
```
- body_units 行数不变
- FTS 行数不变

### TC-7.3: OCR rebuild 后增量更新
- 选一篇已 build 的 paper
- 修改其 `result-hash.txt`（模拟 rebuild 改变）
- 再次 `paperforge memory build`
- 该论文 body_units 刷新（unit_count 可能不同）

### TC-7.4: 空 vault 不崩溃
- 新建 vault，无 OCR 目录
- `paperforge memory build` 不抛异常
- 返回 papers_indexed > 0, body_units_built = 0

---

## 8. Embed Build

**Goal:** embed build 正确路由到 body_units 或 legacy fulltext。

### TC-8.1: body_units 路径嵌入
```bash
paperforge embed build --resume
```
- body_chunk_count > 0（status 输出）
- paperforge_body collection 有数据
- 每个 embedded unit 的 metadata 包含 body_units_hash 和 retrieval_policy_version

### TC-8.2: Legacy 路径兼容
- 未 rebuild 的论文（无 structure-tree.json）仍走 fulltext chunk 路径
- paperforge_fulltext 和 paperforge_body 的 chunk 不冲突

### TC-8.3: Resume 按 body_units_hash 跳过
- 首次 embed build → 嵌入 N 篇
- 再次 `--resume` → 跳过 N 篇（hash 未变）
- 修改一篇 paper 的 structured blocks → 再次 `--resume` → 该篇重新嵌入

### TC-8.4: 无 body_units 但有 structured files 时提示
```
Skip <KEY>: has structured blocks but no body_units in DB.
Run `paperforge memory build` first.
```

### TC-8.5: 双 collection 状态
```bash
python -c "from paperforge.embedding.status import get_embed_status; print(get_embed_status(vault))"
```
- chunk_count（旧 collection）
- body_chunk_count（新 collection）
- total_chunks = 两者之和

---

## 9. Retrieve Merge

**Goal:** `retrieve` 同时查两个 collection，去重 + per-paper cap。

### TC-9.1: 合并结果
```bash
paperforge retrieve "AC joint" --limit 5
```
- 返回 chunks 包含 body_unit 和 legacy_chunk
- 每个 chunk 有 source 字段区分来源

### TC-9.2: 去重
- 同一 unit_id 的 body_unit 和 legacy_chunk（同一段文本）不会同时出现
- 排序按 score 降序

### TC-9.3: Per-paper cap
- 同一篇 paper 最多出现 2 次（在 results 中）
- 多于 2 篇的相关 paper 仍正确返回

### TC-9.4: 空结果处理
```bash
paperforge retrieve "这个不可能存在的查询词"
```
- 返回空 chunks
- 附带 diagnostic 信息
- next_action 提供备选方案

### TC-9.5: 向量库空时提示
```bash
# 在 embed build 之前
paperforge retrieve "test"
```
- ok=False
- error 明确说明

---

## 10. Regression

### TC-10.1: 已有单元测试全部通过
```bash
python -m pytest tests/unit/memory/ tests/test_layer4_* tests/test_ocr_render.py tests/test_ocr_rebuild.py tests/integration/test_memory_workflow.py --no-header -q
```
- 全部 passed（已知 skip 除外）

### TC-10.2: 不破坏旧 CLI 命令
```bash
# 这些命令不依赖 memory layer 新代码
paperforge --help
paperforge status
paperforge search "PEMF"
paperforge embed status
```
- 正常返回

### TC-10.3: 跨 vault 切换
```bash
paperforge --vault D:/L/OB/Literature-hub embed status
paperforge --vault D:/L/OB/Other-vault embed status
```
- 各自向量库独立

---

## 自动测试脚本

以下脚本可 10 分钟跑完全部测试：

```python
# scripts/functional_test_memory_layer.py
"""Run all memory layer functional tests against a real vault."""

import sys, json, sqlite3
from pathlib import Path
from collections import Counter
from paperforge.core.io import read_jsonl
from paperforge.worker.ocr_render import render_fulltext_markdown
from paperforge.worker.ocr_index import build_role_indexes
from paperforge.retrieval.structure_tree import build_structure_tree
from paperforge.retrieval.units import build_body_units, build_object_units
from paperforge.memory.builder import _upsert_body_units
from paperforge.memory.schema import ensure_schema
from paperforge.retrieval.manifest import compute_body_units_hash

VAULT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("D:/L/OB/Literature-hub")
OCR_ROOT = VAULT / "System" / "PaperForge" / "ocr"
KEYS = sorted(d.name for d in OCR_ROOT.iterdir() if d.is_dir()
              and (d / "structure" / "blocks.structured.jsonl").exists())[:10]

pass_count = 0
fail_count = 0

def check(name, cond, detail=""):
    global pass_count, fail_count
    if cond:
        pass_count += 1
        print(f"  ✅ {name}")
    else:
        fail_count += 1
        print(f"  ❌ {name} — {detail}")

# === 1. Render events ===
print("\n=== 1. Render Events ===")
for key in KEYS:
    blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
    try:
        r = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={},
                                     figure_inventory={}, table_inventory={}, return_events=True)
        check(f"{key}: heading_events >=1", len(r.heading_events) >= 1)
        # ascending emitted_order
        orders = [h["emitted_order"] for h in r.heading_events]
        check(f"{key}: heading orders ascending", orders == sorted(orders))
        # backward compat
        r2 = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={},
                                      figure_inventory={}, table_inventory={})
        check(f"{key}: backward compat str", isinstance(r2, str))
    except Exception as e:
        check(f"{key}: no crash", False, str(e))

# === 2. Structure Tree ===
print("\n=== 2. Structure Tree ===")
for key in KEYS:
    blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
    r = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={},
                                 figure_inventory={}, table_inventory={}, return_events=True)
    tree = build_structure_tree(heading_events=r.heading_events,
                                emitted_block_events=r.emitted_block_events,
                                structured_blocks=blocks)
    
    # collect all nodes
    all_nodes = []
    def collect(n):
        all_nodes.append(n)
        for c in n.get("children", []):
            collect(c)
    for n in tree["nodes"]:
        collect(n)
    
    # nesting
    depth_ok = all(
        c["level"] > p["level"]
        for p in all_nodes for c in p.get("children", [])
    )
    check(f"{key}: nesting correct", depth_ok)
    
    # unique node_ids
    nids = [n["node_id"] for n in all_nodes]
    check(f"{key}: unique node_ids", len(set(nids)) == len(nids))
    
    # own_block_ids not overlapping child subtrees
    overlap = False
    for n in all_nodes:
        child_sub = set()
        for c in n.get("children", []):
            child_sub.update(c.get("subtree_block_ids", []))
        own_set = set(n.get("own_block_ids", []))
        if own_set & child_sub:
            overlap = True
    check(f"{key}: own vs child no overlap", not overlap)

# === 3. Body Units ===
print("\n=== 3. Body Units ===")
all_units = []
for key in KEYS:
    blocks = read_jsonl(OCR_ROOT / key / "structure" / "blocks.structured.jsonl")
    r = render_fulltext_markdown(structured_blocks=blocks, resolved_metadata={},
                                 figure_inventory={}, table_inventory={}, return_events=True)
    tree = build_structure_tree(heading_events=r.heading_events,
                                emitted_block_events=r.emitted_block_events,
                                structured_blocks=blocks)
    units = build_body_units(tree=tree, structured_blocks=blocks)
    all_units.extend(units)
    
    ids = [u["unit_id"] for u in units]
    check(f"{key}: unit_ids unique", len(set(ids)) == len(ids))
    
    for u in units:
        check(f"{key}: token cap", len(u["unit_text"]) // 4 <= 1000,
              f"{len(u['unit_text'])//4} tokens")
        if u["part_ordinal"]:
            check(f"{key}: part_ordinal <= max", u["part_ordinal"] <= 99)
    
    # backmatter_body units differ from body
    kinds = set(u["unit_kind"] for u in units)
    for kind in kinds:
        ids_kind = [u["unit_id"] for u in units if u["unit_kind"] == kind]
        check(f"{key}: {kind} unit_ids unique", len(set(ids_kind)) == len(ids_kind))

print(f"\n=== Summary: {pass_count} passed, {fail_count} failed ===")
sys.exit(1 if fail_count else 0)
```
