# Memory Layer 改造设计

> 设计讨论：2026-07-06
> 状态：设计稿（待实施）
> 关联设计：`2026-07-04-layer4-retrieval-substrate-design.md`

---

## 1. 背景与动机

### 1.1 当前问题

1. **结构树 (structure-tree) 是平的** — `children` 永远为 `[]`，没有真实嵌套层级。`level` 只有 1 或 2（来自 `section_heading` / `subsection_heading` 二元角色），无法表达 depth 3/4/5。
2. **`section_path` 靠猜** — 从上一个 heading 的标题推断父子关系，在多同级子节时路径错误。
3. **`structured-blocks.json` 路径不存在** — memory builder 期望 `{ocr_dir}/structured-blocks.json`，但 rebuild 实际写入 `{ocr_dir}/structure/blocks.structured.jsonl`（jsonl 格式）。导致 body_units 永远 0 行。
4. **memory build 的 fast-path 门控太宽** — `canonical_index_hash` 不变时完全跳过重建，但 rebuild 产生的结构化数据变化（`ocr_result_hash` 变了）不被感知。
5. **向量库单 collection** — 旧 chunker 和 新 body_units 共用同一 collection，无法增量迁移。

### 1.2 核心原则

- **Structure-first**：利用论文结构与边界信息，优先使用 body_units 作为检索单元
- **增量切换，用户无感**：旧 chunker 逐步替换为 body_units，rebuilt 论文自动迁移
- **完整路径追踪**：每个 body unit 记录从根到叶子的完整 section_path
- **FTS 兜底**：body_units_fts 是默认正文检索，内容 discovery 不再自动 fallback 到 metadata
- **单一生产者**：Memory Builder 是 body_units 的唯一生产者，Embedding Builder 从 paperforge.db 读取，不重复构建

---

## 2. 数据流全景

```
OCR / Rebuild
  ↓
structure/blocks.structured.jsonl      ← 最终 role blocks
fulltext.md                            ← renderer 已有 H1-H6 heading 层级
index/structure-tree.json              ← 从 H1-H6 + structured blocks 建真实树
index/role-index.json
index/result-hash.txt / manifest hash
  ↓
Memory Builder (build_from_index)
  ↓
paperforge.db
  ├─ papers / aliases / paper_fts       ← 论文元数据检索
  ├─ body_units                         ← 正文结构化检索单元（唯一生产者）
  ├─ body_units_fts                     ← 正文 FTS
  ├─ object_units                       ← figure / table / object 周边证据
  └─ manifest:<key>                     ← 每篇 OCR 结果 hash / policy hash
  ↓
Embedding Builder (读取 DB body_units，不重新构建)
  ├─ paperforge_fulltext                ← 旧 chunker，兼容旧论文
  └─ paperforge_body                    ← 新 body_units
  ↓
Retrieve / Content Discovery
  ├─ content-discovery → body_units_fts
  ├─ retrieve → fulltext + body 双 collection 合并
  └─ paper-lookup → metadata / aliases
```

---

## 3. 结构树改造 (Structure Tree)

### 3.1 现状问题

当前 `retrieval/structure_tree.py` 的 `build_structure_tree()` 从 structured blocks 的 `role` 字段读取 heading，但只有 `section_heading` / `subsection_heading` 二元区分，丢失了 H3-H6 的层级信息。

### 3.2 改造方案

从 `fulltext.md` 的 H1-H6 标记读 heading 层级。但 **不通过 fuzzy title match 反推 block_id**——Methods / Results 等重复标题会导致歧义。

**方案：render 阶段产出 heading-map.json sidecar**

```json
{
  "headings": [
    {"line_number": 42, "markdown_level": 3, "title": "Study population",
     "page": 2, "block_id": "b_10"}
  ]
}
```

写入位置：`render/heading-map.json`，与 `render/fulltext.md` 同时产出。
`build_structure_tree()` 读 `render/heading-map.json` + `structured_blocks`，不从 markdown 反推 block_id。

**算法（PaperIndex 的 stack 算法）：**

```
for each heading in heading_map（按 page + line_number 顺序）:
  while stack 不空 and stack[-1].level >= current.level:
    stack.pop()
  if stack 不空:
    stack[-1].children.append(current)
  else:
    root_nodes.append(current)
  stack.append(current)
```

### Phase 5 顺序约束（关键）

新版依赖 `render/heading-map.json`，但当前 rebuild Phase 5 的顺序是先建树、后写 render：

```
× build_structure_tree(structured)     → 先建树（无 heading-map）
× write_structure_tree(index/)
× write_render_outputs(...)             → 后写 render（含 heading-map）
```

**必须改成：**

```
1. write_render_outputs(..., heading_events=heading_events)
2. build_structure_tree(heading_events, structured_blocks)
3. write_structure_tree(index/structure-tree.json)
```

更干净的做法：`render_fulltext_markdown()` 直接返回 `(markdown, heading_events)`，`write_render_outputs()` 写 markdown + heading-map，`build_structure_tree_from_heading_events()` 用内存中的 heading_events，不再读文件。

### 3.3 每个节点的字段

```python
{
  "node_id": "sec:<block_id>",
  "kind": "section",
  "title": "Study population",
  "level": 3,                           # H1=1, H2=2, ..., H6=6
  "section_path": [                      # 完整祖先链
    "Materials and methods Design",
    "2.1 Study Design",
    "2.1.1 Study population"
  ],
  "page_span": [2, 3],
  "own_block_ids": ["b_10", "b_11"],    # 只属于当前节点本体的 block_ids
                                         # 范围 = 从当前 heading 到第一个 child heading 前
  "subtree_block_ids": ["b_10".."b_25"], # 整个 subtree 的 block_ids（含子节点）
  "children": [],
  "objects": []
}
```

### 3.4 own_block_ids vs subtree_block_ids（关键修正）

父节点的 block_span 如果定义为"从当前 heading 到下一个同级/更高级 heading"，则会包含所有子节内容。递归构建 body unit 时，子节正文会被重复纳入父 unit。

且"当前 heading → 第一个 child heading 前"会漏掉子节结束后又回到父节的内容（如 Discussion 开头的 intro + 中间的子节 + 结尾的 summary）。

**修正：拆成两个概念**

| 字段 | 含义 | 用途 |
|------|------|------|
| subtree_block_ids | 整棵 subtree 的 block_ids（含所有子孙节点） | 导航/scope fetch |
| own_block_ids | subtree_block_ids − 所有 child.subtree_block_ids − heading blocks | body unit 正文 |

`own_block_ids` = 当前节点 subtree 内**不属于任何子节点 subtree** 的直接内容。这自动覆盖：
- 父节 intro（第一个 child 前）
- 父节 child 后面的 summary/transition
- 父节中间未归入子节的段落

举例：

```
## Discussion
  intro paragraph                    ← own
  ### Mechanism
    mechanism text                   ← child subtree
  ### Limitation
    limitation text                  ← child subtree
  summary paragraph                  ← own（子节结束后回到父节）

Discussion.own_block_ids     = [intro_para, summary_para]
Discussion.subtree_block_ids = [intro_para, mechanism_text, limitation_text, summary_para]
```

### 阅读顺序依赖（关键）

`own_block_ids` / `subtree_block_ids` 的 interval 计算必须基于 **renderer 的最终阅读顺序**，而非 structured_blocks 的原始列表顺序。

原因：structured_blocks 经过双栏重排、tail reorder、reference zone 移序等处理后，block 顺序已不等于最终阅读顺序。

**做法：**

Renderer 输出 `render/block-order-map.json`（或 heading_events 同时记录 `emitted_order`）。每个 entry：`{block_id, page, emitted_order, role}`。

Tree builder 在计算 subtree interval 前，先将 structured_blocks 按 `emitted_order` 重排。`subtree_block_ids` 在当前节点 heading 的 `emitted_order` 到下一个同级 heading 的 `emitted_order` 之间选取。然后按 `subtree − descendants` 计算 `own_block_ids`。

如果 PR 1 暂不做完整 `block-order-map`，至少让 heading-map 每条记录 `emitted_order`，tree builder 依赖 heading 顺序而非 blocks 顺序。

## 4. Body Units 生成

### 4.1 单一生产者原则

**Memory Builder 是 body_units 的唯一生产者。** Embedding Builder 从 paperforge.db.body_units 读取 indexable=1 的行，不重新调用 build_body_units()。这样保证 FTS 和 vector 用同一批 unit。

### 4.2 build_body_units() 算法

使用 role helper 统一处理正文角色和 backmatter 角色：

```python
def _body_unit_role_kind(role: str) -> str | None:
    if role == "body_paragraph":
        return "body"
    if role in {"structured_insert", "non_body_insert", "backmatter_body"}:
        return "backmatter_body"
    return None  # reference_item / reference_heading / heading / caption / asset → excluded


def build_body_units(*, tree: dict, structured_blocks: list[dict]) -> list[dict]:
    units = []

    def walk(node, inherited_path=[]):
        this_path = inherited_path + [node["title"]]

        # 收集 own_block_ids 中 body_paragraph / backmatter 的 blocks
        own_blocks = [
            b for b in structured_blocks
            if b["block_id"] in node.get("own_block_ids", [])
            and _body_unit_role_kind(b.get("role", "")) is not None
        ]

        if own_blocks:
            # 按 unit_kind 分组（body / backmatter_body 不混）
            from itertools import groupby
            groups = []
            for kind, grp in groupby(own_blocks, key=lambda b: _body_unit_role_kind(b.get("role", ""))):
                if kind:
                    groups.append((kind, list(grp)))

            for unit_kind, blocks in groups:
                all_text = "\n\n".join(b.get("text", "") for b in blocks)
                parts = _split_if_oversized(all_text, max_tokens=1000)
                n_parts = len(parts)
                for p_idx, part_text in enumerate(parts):
                    part_ordinal = p_idx + 1 if n_parts > 1 else 0
                    suffix = f":part_{part_ordinal:03d}" if part_ordinal else ""
                    uid = f"{paper_id}:body:{node['node_id']}{suffix}"
                    unit = {
                        "unit_id": uid,
                        "paper_id": paper_id,
                        "section_path": "/".join(this_path),
                        "section_path_json": json.dumps(this_path),
                        "section_level": node["level"],
                        "section_title": node["title"],
                        "page_span": node["page_span"],
                        "unit_text": part_text,
                        "token_estimate": len(part_text) // 4,
                        "unit_kind": unit_kind,
                        "part_ordinal": part_ordinal,
                        "indexable": True,
                        "veto_reason": "",
                        "quality_hints": [],
                    }
                    units.append(unit)
```
### 4.3 Token Cap 与拆分

leaf section 的 token_estimate 超过 1000 时，按 paragraph boundary 拆分为多个 part。拆分后保留相同的 section_path / section_title / section_level，加 part_ordinal。

```
unit_id:
  paper:body:sec_node_id            ← 单块（≤1000 tokens）
  paper:body:sec_node_id:part_001   ← 多块
  paper:body:sec_node_id:part_002
REM

### 4.4 输出格式

```python
{
    "unit_id": "23T2B8ZX:body:sec_10:e2-e10:e2-e14",
    "paper_id": "23T2B8ZX",
    "section_path": "Materials and methods/Study population",
    "section_path_json": '["Materials and methods", "Study population"]',
    "section_level": 3,
    "section_title": "Study population",
    "page_span": [2, 2],
    "unit_text": "...",
    "token_estimate": 508,
    "unit_kind": "body",
    "part_ordinal": 1,       # 0 = 单块, 1+ = 拆分序号
    "indexable": True,
    "veto_reason": "",
    "quality_hints": [],
}
```

### 4.5 Backmatter / References 处理

| 内容类型 | role | 进 body_units? | unit_kind | indexable |
|---------|------|---------------|-----------|-----------|
| 正文段落 | body_paragraph | ✅ | "body" | True |
| 致谢/数据声明/作者贡献 | structured_insert / non_body_insert | ✅ | "backmatter_body" | True |
| 参考文献条目 | reference_item | ❌ 不进 body_units | — | — |
| References 标题 | reference_heading | ❌ | — | — |

reference_item 不进 body_units：否则 query 作者名/期刊名时会命中 references 而非正文证据。

### 4.6 _upsert_body_units() 增量安全

per-paper 精确刷新，避免全库 FTS 重建的重复/残留风险：

```python
def _upsert_body_units(conn, body_units: list[dict]):
    paper_ids = list({u["paper_id"] for u in body_units})
    for pid in paper_ids:
        conn.execute("DELETE FROM body_units WHERE paper_id = ?", (pid,))
        conn.execute("DELETE FROM body_units_fts WHERE paper_id = ?", (pid,))
    for unit in body_units:
        conn.execute("""INSERT INTO body_units (...) VALUES (...)""", ...)
    for pid in paper_ids:
        conn.execute("""INSERT INTO body_units_fts(...)
                        SELECT rowid, unit_id, paper_id, section_path, unit_text
                        FROM body_units
                        WHERE paper_id = ? AND indexable = 1""", (pid,))
```

---

## 5. Object Units 适配嵌套树

当前 `build_object_units()` 也是 flat node 遍历。树变 nested 后，父节点 span 包含 child object，同样出现重复归属。

**修正：** object ownership 只匹配 own_block_ids 范围。

一个 object 只归属一个最具体的 section（own_block_ids 匹配的最深节点）。

---

## 6. Memory Builder 增量逻辑

### 6.1 改造后流程

```
build_from_index(vault):
  1. 计算 canonical_index_hash
  2. 检查 canonical_index_hash 是否匹配
     ├─ 匹配（index 未变）：
     │   a. 跳过 papers / aliases / FTS 重建
     │   b. 继续到步骤 3
     │
     └─ 不匹配（index 变了）：
         a. 全量重建
         b. 跳过步骤 3

  3. Per-paper body_units 增量更新
     for each paper with tree + blocks.structured.jsonl:
       读取 manifest:<key> 的 ocr_result_hash
       计算当前 ocr_result_hash
       ├─ 相同 → skip
       └─ 不同或缺失 → 重建 body_units + object_units + 更新 manifest
```

### 6.2 ocr_result_hash 三级 fallback

```python
def _resolve_ocr_result_hash(paper_dir: Path) -> str:
    # 1. index/result-hash.txt
    rp = paper_dir / "index" / "result-hash.txt"
    if rp.exists():
        return rp.read_text().strip()
    # 2. hash of 结构化产物
    hasher = hashlib.sha256()
    for rel in ["structure/blocks.structured.jsonl",
                "index/structure-tree.json",
                "index/role-index.json"]:
        p = paper_dir / rel
        if p.exists():
            hasher.update(p.read_bytes())
    result = hasher.hexdigest()
    if result != hashlib.sha256(b"").hexdigest():
        return result
    # 3. meta.json derived_version
    meta_p = paper_dir / "meta.json"
    if meta_p.exists():
        meta = json.loads(meta_p.read_text())
        dv = meta.get("derived_version", {})
        return hashlib.sha256(json.dumps(dv, sort_keys=True).encode()).hexdigest()
    return ""
```

### 6.3 Manifest 与 Vector 共用 body_units_hash

manifest 和 vector resume 使用**同一个 canonical hash**，命名统一为 `body_units_hash`。

```python
def compute_body_units_hash(units: list[dict], policy_version: str) -> str:
    raw = json.dumps([{
        "unit_id": u["unit_id"],
        "section_path": u["section_path"],
        "section_level": u["section_level"],
        "section_title": u["section_title"],
        "unit_kind": u["unit_kind"],
        "part_ordinal": u["part_ordinal"],
        "unit_text": u["unit_text"],
        "retrieval_policy_version": policy_version,
    } for u in units], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()
```

**存储位置：**

```text
meta manifest:<key>  → body_units_hash
vector metadata       → body_units_hash（每条向量都存）
embed build-state    → 用于 resume 比较
```

这样 manifest 判断和 vector resume 判断始终对齐。

### 7.2 Embedding Builder 从 DB 读取

```python
def get_body_units_for_embedding(vault, zotero_key) -> list[dict]:
    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=True)
    rows = conn.execute(
        """SELECT unit_id, paper_id, section_path, section_level, section_title,
                  unit_kind, part_ordinal, unit_text, token_estimate
           FROM body_units
           WHERE paper_id = ? AND indexable = 1
           ORDER BY unit_id""",
        (zotero_key,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

SELECT 必须包含所有 `body_units_hash` 计算字段，否则 hash 会用 None 做 silent input。

### 7.3 embed_body_units()

```python
RETRIEVAL_POLICY_VERSION = "l4.body.v1"

def embed_body_units(vault, zotero_key, body_units):
    collection = get_collection(vault, name="paperforge_body")
    provider = OpenAICompatibleProvider(vault)

    body_units_hash = compute_body_units_hash(body_units, RETRIEVAL_POLICY_VERSION)

    texts = [u["unit_text"] for u in body_units]
    ids = [u["unit_id"] for u in body_units]
    metadatas = [{
        "paper_id": zotero_key,
        "section_path": u["section_path"],
        "section_level": u["section_level"],
        "section_title": u["section_title"],
        "chunk_index": u["unit_id"],
        "token_estimate": u["token_estimate"],
        "unit_kind": u["unit_kind"],          # "body" or "backmatter_body"
        "part_ordinal": u["part_ordinal"],
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
        "body_units_hash": body_units_hash,
    } for u in body_units]

    embeddings = provider.encode(texts)
    collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return len(body_units)
```

### 7.4 delete_paper_vectors() 双删

```python
def delete_paper_vectors(vault, zotero_key):
    for name in ["paperforge_fulltext", "paperforge_body"]:
        try:
            collection = get_collection(vault, name=name)
            ids = collection.get(where={"paper_id": zotero_key}).get("ids", [])
            if ids:
                collection.delete(ids=ids)
        except Exception:
            pass
```

### 7.5 Resume 检测（body_units_hash + policy_version）

仅比较 `retrieval_policy_version` 不够——文本变化时不会触发重嵌。

**判断逻辑：**

```
if paperforge_body 中存在该 paper_id
  且 stored.body_units_hash == current.body_units_hash
  且 stored.retrieval_policy_version == current.retrieval_policy_version
  → skip

否则：
  delete + re-embed
```

`current.body_units_hash` 由 `compute_body_units_hash(body_units, policy_version)` 计算，与 manifest 使用同一函数。

### 7.6 embed status 内部分 collection 统计

对外总数，对内明细：

```json
{
  "chunk_count": 61258,
  "collections": {
    "paperforge_fulltext": 60225,
    "paperforge_body": 1033
  }
}
```
REM
REM

---

## 8. Retrieve 双 Collection 合并

### 8.1 merge_retrieve() 签名

```python
def merge_retrieve(vault, query, limit=5, expand=True) -> list[dict]:
```

### 8.2 合并逻辑

1. 查 paperforge_fulltext + paperforge_body
2. unit-level 去重（legacy: collection+id, body: unit_id）
3. per-paper cap：每篇最多 2-3 条（不按 paper_id 一条去重——同一篇论文的不同 section 都可能命中）
4. 标注 source: legacy_chunk / body_unit
5. score 降序，截取 top limit

---

## 9. Content Discovery 行为

### 9.1 核心规则

- body_units_fts 为 primary 检索源
- 无结果时不静默 fallback 到 paper_fts（metadata 搜索）
- 返回 coverage 信息（denominator 固定）：
  body_units_papers  = COUNT(DISTINCT paper_id) FROM body_units WHERE indexable=1
  ocr_done_papers    = COUNT(*) FROM papers WHERE ocr_status='done'
  library_papers     = COUNT(*) FROM papers
- UI 建议显示：`正文索引覆盖 body_units_papers / ocr_done_papers 篇 OCR 完成论文`
- metadata 搜索只作为显式 next_action

### 9.2 混合迁移 coverage 保护

22 篇有 body_units 时 body_units_fts.count > 0，content-discovery 会自动切到 body_units_fts 路径。此时 846 篇旧论文不可见。不做静默 fallback，但 coverage 提示让用户知道搜索范围有限。

---

## 10. SQLite Schema 调整

body_units 表补充字段（CURRENT_SCHEMA_VERSION → 4）：

```sql
section_path_json TEXT NOT NULL DEFAULT '[]',
section_level    INTEGER NOT NULL DEFAULT 0,
section_title    TEXT NOT NULL DEFAULT '',
part_ordinal     INTEGER NOT NULL DEFAULT 0,
```

---

## 11. PR / Wave 拆分

### PR 1：结构树和 body_units 正确性（最核心）
- core.io.read_jsonl（待加）
- render/heading-map.json sidecar（renderer 同步产出）
- build_structure_tree() — stack 算法，own_block_ids
- build_body_units() — recursive，own_block_ids，token cap
- build_object_units() — recursive，own_block_ids
- schema 字段扩展 + version 4
- tests: 嵌套路径、parent 不重复、空壳跳过、token cap

### PR 2：Memory Builder 增量
- 路径修正（待改）
- 不 early return on canonical_hash
- per-paper ocr_result_hash 增量
- _resolve_ocr_result_hash 三级 fallback
- _upsert_body_units per-paper FTS 精确刷新

### PR 3：Content Discovery 行为
- body_units_fts primary
- 无结果时不 fallback
- coverage 提示

### PR 4：Embedding 双 collection
- get_collection(name=)
- embed_body_units()
- delete_paper_vectors() 双删
- embed build 从 DB 读 body_units
- resume 检测 body_unit_hash + policy_version
- status 分 collection 统计

### PR 5：Retrieve 合并
- merge_retrieve()
- unit-level dedup + per-paper cap
- retrieve.py 切到 merge_retrieve()
- 输出 source 标注

---

## 12. 边界情况与风险

| 场景 | 处理方式 | 风险 |
|------|---------|------|
| 0 篇有 blocks.structured.jsonl | 全部走旧 chunker | 🟢 无 |
| 部分论文有（22/868） | 分流处理 | 🟡 注意 content-discovery coverage |
| 父节点 own 包含子内容 | 已拆为 own / subtree | 🟢 已处理 |
| body_units > 1000 tokens | token cap 拆分 | 🟢 已处理 |
| References 污染正文检索 | reference_item 不进 body_units | 🟢 已处理 |
| result-hash.txt 不存在 | 三级 fallback hash | 🟡 已处理 |
| resume 命中旧策略版本或文本变了 | vector metadata 存 body_unit_hash + policy_version | 🟢 已处理 |
| content-discovery 只搜 22 篇 | coverage 提示 | 🟡 用户可见 |
