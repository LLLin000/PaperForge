# discover-papers

从文献库中发现和检索论文，返回候选清单（candidate list）。

---

## Pre-flight Checklist

进入此 molecule 前，确认以下检查已完成。每项完成后标记 `[x]`：

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON`、`$LIT_DIR` 已从 bootstrap 获取
- [ ] `capabilities` 已读取（至少确认 `metadata_search` 可用）
- [ ] intent 已确定为 `discover_papers`

---

## 步骤

### Step 1: 解析用户搜索意图

提取以下信息（缺什么就问用户）：
- **搜索词**：关键词、作者名、年份
- **范围**：domain（如"骨科"）、不指定=全库
- **过滤条件**：OCR 状态、年份范围（`--year-from`/`--year-to`）、lifecycle

### Step 2: 多臂搜索策略

打开 `atoms/retrieval-routing.md` 参照 Ladder A。

**先检查 `retrieve` 是否可用：**

```bash
$PYTHON -m paperforge --vault "$VAULT" embed status --json
```

取 `data.db_exists` 和 `data.chunk_count`。仅当 `db_exists == true && chunk_count > 0` 时 `retrieve` 可用。

**根据用户意图选择搜索臂：**

| 用户说...                           | 执行臂                              |
|--------------------------------------|-------------------------------------|
| 技术术语/方法/参数（"bipolar pulses"、 "galvanotaxis"） | 先用 **Arm 1**（全文语义）再 **Arm 2**（元数据补充） |
| 作者+年份、主题关键词               | **Arm 2**（元数据）为主，可选 Arm 1 |
| "collection X里有什么" / "库里有什么" | **Arm 3** （collection 列举）       |
| 宽泛主题                             | **Arm 1** 先搜，**Arm 2** 补充      |

#### Arm 1 — 全文语义搜索（仅当 `retrieve` 可用）

```bash
$PYTHON -m paperforge --vault "$VAULT" retrieve "<query>" --json --limit 30
```

- 搜索 OCR 全文块的向量嵌入，能匹配正文 Methods/Results/Discussion 中的概念
- 返回 JSON：`data.chunks[]` 包含 `paper_id`（即 `zotero_key`）、`section`、`page_number`、`chunk_text`
- 从 chunks 中提取唯一 paper_id 列表作为候选论文集合
- 如果 `ok: false` → 跳过此臂

#### Arm 2 — 元数据 FTS 搜索（始终可用）

```bash
$PYTHON -m paperforge --vault "$VAULT" search "<query>" --json --limit 30 \
    [--domain "<domain>"] \
    [--year-from <N>] [--year-to <N>] \
    [--ocr <done|pending|failed|processing>] \
    [--lifecycle <indexed|pdf_ready|fulltext_ready|deep_read_done>]
```

- FTS5 搜索标题、摘要、作者、期刊、domain、collection 路径
- 返回 JSON：`data.matches[]` 包含 `zotero_key`、`title`、`year`、`first_author` 等

#### Arm 3 — Collection/Domain 列举（完整列表，不截断）

```bash
$PYTHON -m paperforge --vault "$VAULT" context --collection "<collection_path>" --json
$PYTHON -m paperforge --vault "$VAULT" context --domain "<domain>" --json
```

- 返回 collection 或 domain 下**所有**论文（无 limit 截断）
- `context --collection` 按 collection 路径前缀匹配
- `context --domain` 按 domain 字段精确匹配
- 如果列表超过 50 篇，按年份/作者分组摘要后问用户是否缩小范围

#### 结果去重

- 合并所有臂的结果
- 按 `zotero_key` 去重（保留首次出现）
- 如果同时用了 Arm 1+2：优先保留 Arm 1 的结果（包含全文命中信号）
- 去重后进入 Step 3 富化

#### 大规模结果集处理

- 如果任何一臂返回超过 20 篇，告知用户总数
- 主动提供选项：加 limit、按年份/domain/作者缩小、只展示前 N 篇
- 不要跳过或隐瞒大量结果的存在

#### 当 `retrieve` 不可用时的降级

如果 `embed status` 显示无向量索引：

> 语义全文搜索不可用（向量索引未构建）。已降级到元数据搜索。运行 `paperforge embed build` 后可开启正文发现。

然后只运行 Arm 2（或 Arm 3 如果是 collection/domain 查询）。

### Step 3: Top-hit 富化（`paperforge paper-context`）

对候选列表中的 **前 10 篇**（如果超过 10 篇，只富化前 10），调 `paper-context` 获取详细状态：

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <zotero_key> --json
```

目的：拿到 `ocr_status`、`prior_notes` 数量、`analyze` 状态，帮助用户判断哪些可以直接读。

如果列表超过 10 篇，在展示时告知用户总数和只富化了前 N 篇。

### Step 4: 展示候选清单

格式（每条一行）：

```
找到 N 篇匹配 "<query>"（来自 [全文语义/元数据/collection列举]）：

[1] ABC12345 | Smith 2024 | 论文标题 | 骨科 | OCR: done | 精读: pending | 阅读笔记: 3
[2] DEF67890 | Jones 2023 | 论文标题 | 骨科 | OCR: done | 精读: done   | 阅读笔记: 0
[3] GHI11111 | Wang 2022  | 论文标题 | 骨科 | OCR: pending |           | 阅读笔记: 0

（共 N 篇，仅展示前 M 篇。如需查看更多，请说"更多"或指定年份/关键词缩小范围）
```

关键字段：`zotero_key`、`first_author`、`year`、`title`、`domain`、`ocr_status`、`deep_reading_status`

**来源标注**：如果使用了多臂搜索，在顶部标注命中来自哪个搜索臂（`全文语义` / `元数据` / `collection列举`）。

### Step 5: 等用户选择后续操作

展示候选后不要自己决定下一步。等用户说：
- "读一下 [1]" → 路由到 `read-known-paper.md`
- "精读 [2]" → 路由到 `deep-analyze-paper.md`
- "换个关键词" / "refine" → 回到 Step 1
- "不找了" → 结束

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 用户选了一篇论文 | `read-known-paper.md` |
| 用户想重新搜索、缩小范围 | 返回 Step 1（refine） |
| 用户想精读（deep read） | `deep-analyze-paper.md` |

---

## 禁止

- 不要在搜索结果中替用户决定读哪篇
- 不要在搜索阶段读全文
- 不要对 0 结果硬猜路径
