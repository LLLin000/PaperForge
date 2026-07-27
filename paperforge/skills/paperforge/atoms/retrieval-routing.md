# retrieval-routing

**Agent 检索决策的唯一事实源。**

这个 atom 定义 Agent 如何调用 PaperForge 检索后端：
1. 判断本次检索的意图
2. 通过 planner 决定执行路径
3. 安全执行一条命令
4. 最多执行一次 fallback
5. 解释结构化结果

> 这是检索路由的**单一权威协议**。molecules 不复制、不绕过这套规则。

---

## 1. Intent Determination

每次检索从三个意图中选定一个：

| Intent | 含义 | 对应用户问题 |
|--------|------|-------------|
| **locate** | 定位一篇已明确的论文 | "帮我找 DOI 10.1234/abcd 的论文"、"查 Smith 2024" |
| **discover** | 发现一批相关论文 | "找 PTOA 相关的文献"、"骨科 collection 里有什么" |
| **content** | 查找正文中的事实/参数/证据 | "这篇用了多少 Hz"、"支持 galvanotaxis 的证据" |

注意：这是**一次检索动作**的 intent，不是 molecule 名称。
molecule 决定工作流编排；retrieval-routing 只决定这一次调用哪条 CLI 路径。

---

## 2. Planner Protocol

**任何检索动作的第一步都是调用 query-plan，不要自行决定用哪个命令。**

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  query-plan "<user_query>" \
  --intent <locate|discover|content> \
  --json
```

### 解析 plannner 输出

读取以下固定字段：

```
data.intent          — 回显本次检索意图
data.query           — 规范化后的检索 query（可能包含改写）
data.scope           — "paper"（单篇范围）| "library"（全库范围）
data.paper_key       — scope=paper 时的 paper identifier；scope=library 时为 null
data.primary         — 推荐命令 + 参数，格式：{"command": "...", "args": {...}}
data.fallback        — 仅当 primary 零结果时使用；null 表示无 fallback
```

### 不再读取的字段（后端已移除，molecules 不得引用）

```
recommended_primary     ← 已简化为 data.primary
query_class             ← 已移除
suggested_modes         ← 已移除
query_writing_rules     ← 已移除
```

---

## 3. Safe Command Executor

`data.primary.command` 和 `data.primary.args` 必须按以下规则渲染为实际 CLI。

### 命令白名单

只允许以下三个命令。planner 返回其他命令时停止并报告 contract mismatch，不要自行猜测。

| command | CLI 形式 |
|---------|----------|
| `paper-context` | `$PYTHON -m paperforge --vault "$VAULT" paper-context <args.key> --json` |
| `search` | `$PYTHON -m paperforge --vault "$VAULT" search "<query>" [--domain] [--year-from] [--year-to] [--ocr] [--limit N] --json` |
| `retrieve` | `$PYTHON -m paperforge --vault "$VAULT" retrieve "<plan.query>" [--paper KEY] [--deep] [--limit N] --json` |

### 关键渲染规则

**`retrieve` 的 query 来自 `plan.query`，不是来自 `args`。** 示例：

```json
{
  "query": "what frequency was used",
  "primary": {
    "command": "retrieve",
    "args": {"paper": "ABCDEFGH"}
  }
}
```

应渲染为：

```bash
$PYTHON -m paperforge --vault "$VAULT" retrieve "what frequency was used" --paper ABCDEFGH --json
```

不是：

```bash
# ❌ 错误—缺少位置参数 query
$PYTHON -m paperforge --vault "$VAULT" retrieve --paper ABCDEFGH
```

### scope safety guard

当 `scope=paper` 时，即使 planner 返回的 fallback 存在，Agent 也**不执行** fallback（见第 4 节）。

---

## 4. Exactly-One-Fallback Protocol

```text
1. 执行 primary 命令
2. 检查结果是否触发 fallback：
   a. primary 返回 error（INTERNAL_ERROR）→ 不触发 fallback，直接报告错误
   b. zero_results（matches 为空，且 scope=library）→ 进入步骤 3
   c. scope=paper 且 zero_results → 不触发 fallback，报告"本文未检索到相关内容"
   d. scope=paper 且 fulltext_unavailable → 报告"本文无可用正文"，不触发 fallback
   e. 有结果 → 直接返回，不触发 fallback
3. 触发 fallback 当且仅当：
   a. data.fallback 不为 null
   b. scope=library（paper scope 不扩域）
4. 执行一次 fallback 命令（同第 3 节渲染规则）
5. fallback 结束后不再二次 fallback，不再重新调用 query-plan
```

**硬规则：**

- 最多一次 fallback
- fallback 后不再调用 query-plan
- fallback 后不再触发第二条 fallback
- `scope=paper` 时永远不得扩大到 library
- "没有直接回答" 定义为：结果存在，但没有包含可用于回答用户问题的正文证据——不能因为分数低就自动 fallback

---

## 5. Evidence Interpretation

primary 或 fallback 返回的 matches 按以下规则解释：

### body 证据（正文）

```yaml
source_kind: "body"
structure_resolved: true
  → 有明确章节归属的正文证据
  → section_title / section_level / part_ordinal 可用

source_kind: "body"
structure_resolved: false
  → 内容存在，但章节所有权未确认
  → 慎用，建议标注"未确认章节位置"

body 结果包含:
  - text: 匹配正文片段
  - node_id: structure tree 节点 ID
  - structure_path: 章节路径数组（["Introduction", "Methods"]）
```

### object 证据（图表）

```yaml
source_kind: "object"
object_kind: "figure" | "table"
  → 图或表证据
  → object_kind 区分类型

object 结果包含:
  - text: 图表标签 + caption + 附近正文
  - node_id: structure tree 节点 ID
  - structure_path: 章节路径
```

### metadata 候选项

```yaml
来自 search 命令:
  fulltext_available: false
  body_units_count: 0
  ocr_status: "pending"
  → 仅元数据候选项，不是正文验证
  → 标注为 "metadata candidate — fulltext not yet available"
```

### 不存在正文时的边界

```yaml
paper scope + fulltext_unavailable:
  → 明确报告限制，不搜索其他论文
  → 不虚构引用位置或片段
```

---

## Session State

一次会话中多个检索请求应复用已获取的信息：

```
paper-key：session 生命周期内复用
  - session 内再次出现同一 paper_key 的请求，直接 retrieve --paper KEY
  - 不重新调用 query-plan，不重新加载 structure

structure：成功后不清除
  - 第一次 paper-context --structure 后缓存
  - 后续同一 paper 的结构问题直接用缓存回答

metadata：不重复调用 paper-context
  - title、first_author、year 从首次 paper-context 或 search 结果保存

重置条件：
  - 用户明确切换论文时重置全部 session state
```

---

## 检索命令说明

### `paper-context` — 论文完整上下文

```
paper-context <KEY> --json
  → paper 元数据 + 状态 + 关联笔记 + prior_notes

paper-context <KEY> --structure --json
  → 附加 StructureTree（论文章节导航地图）

StructureTree 是导航地图，不是全文内容替代品：
  - 用于确定章节父子关系、document order、图表所在章节
  - 详细内容仍由 pf_deep.py prepare + fulltext 提供
  - 不能仅靠 StructureTree 回答事实性问题
```

### `search` — 元数据全文搜索

```
search "<query>" [--domain D] [--year-from Y] [--year-to Y] [--ocr S] [--limit N] --json
  → data.matches[]: zotero_key, title, first_author, year, journal, domain
    fulltext_available, body_units_count, ocr_status

search --evidence flag: 不存在。
  结果是否可作为证据由 fulltext_available 字段决定。
  无需单独 CLI 模式。
```

### `retrieve` — 正文内容检索

```
retrieve "<query>" [--paper KEY] [--deep] [--limit N] --json
  → data.matches[]: zotero_key, unit_id, source_kind, structure_resolved,
    node_id, structure_path, section_title, section_level, part_ordinal,
    text, score, object_kind（仅 object）

--paper KEY: 限定到单篇论文
--deep: 混合检索模式（BM25 + 向量），适用于需要跨章节关联的查询
```

### `query-plan` — 检索规划器

```
query-plan "<query>" --intent <locate|discover|content> --json
```

query-plan 不取数据。它只返回意图分类 + 推荐的执行路径。
所有数据由 paper-context、search、retrieve 三个执行命令返回。

---

## 与旧系统的关系

这个 atom 取代了旧版本的 Ladder A/B/C/D 多臂检索系统：

| 旧机制 | 新机制 |
|--------|--------|
| 手动 embed status → 选 Arm | query-plan 决定 primary |
| 并行组合 retrieve + search | primary → 一次 fallback |
| rg / grep evidence ladder | structure 字段判定证据 |
| retrieve 只是"候选" | retrieve 输出包含结构坐标，可直接作为证据 |

旧文档中涉及的 `data.chunks`、`content-discovery`、`scoped-fetch`、`recommended_primary`、`Arm 1/2/3` 均已废弃。
