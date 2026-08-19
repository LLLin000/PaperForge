# discover-papers

从文献库中发现和检索论文，返回候选清单。

> 这个 molecule 只编排工作流。**检索决策由 `atoms/retrieval-routing.md` 决定。**

---


## 步骤

### Step 1: 解析搜索意图

提取用户搜索意图中的要素（缺什么就问用户）：
- **搜索词**：关键词、作者名、年份
- **范围**：domain（如"骨科"）、不指定 = 全库
- **过滤**：年份范围、OCR 状态

discover 属于 Route C(模糊/跨库),直接跑 search,不调用 query-plan:

```bash
$PYTHON -m paperforge --vault "$VAULT" \
  search "<关键词>" [--domain <domain>] [--year-from <Y>] [--year-to <Y>] --limit 10 --json
```

READ ONLY:`data.matches[]`(每项 `zotero_key` / `first_author` / `year` /
`title` / `domain` / `fulltext_available` / `ocr_status`)。

matches 空 → 按 `atoms/retrieval-routing.md` §4 跑一次 retrieve 后停止,不二次
fallback。

### Step 2: 去重展示

按 `atoms/retrieval-routing.md` §4 结果处理:search 命中展示元数据候选;
retrieve fallback 只展示命中章节/片段/score,不虚构 title/author/year。

### Step 3: 按 zotero_key 去重
**primary 来自 search 时：**

```
找到 N 篇匹配 "<query>"：

[1] ABC12345 | Smith 2024 | 论文标题
    Fulltext: available | OCR: done
[2] DEF67890 | Jones 2023 | 论文标题
    Fulltext: false | OCR: pending
```

每项展示：`zotero_key`、`first_author`、`year`、`title`、`domain`、`fulltext_available`、`ocr_status`。

**fallback 来自 retrieve 时**（retrieve 输出不保证包含 title/author/year）：

```
正文检索结果：

[1] ABC12345 | Methods | score: 0.85
    "75 Hz bipolar stimulation was applied..."
[2] DEF67890 | Results | score: 0.72
    "frequency of 75 Hz showed significant effect..."
```

按 `zotero_key` 聚合，只展示命中章节、片段和 score。不虚构 title/author/year。

**object hit（图表结果）：** 作为"该论文命中了相关图表"的候选信号。
不展开 object 的正文引用——discover 只返回候选，图表上下文由 `read-known-paper` 或
`find-supporting-evidence` 中的 Object evidence 协议处理。

用户选中某篇后，由 `read-known-paper` 获取完整 metadata。
只有用户选中某篇后，才进入 `read-known-paper` 并调用 paper-context。
### Step 5: 等待用户选择

展示后不要自己决定下一步。等用户说：

- "读一下 [1]" → `read-known-paper.md`
- "精读 [2]" → `deep-analyze-paper.md`
- "换个关键词" → 回到 Step 1
- "不找了" → 结束

---

## 过渡路由

| 用户动作 | 路由目标 |
|---------|---------|
| 用户选了一篇论文 | `read-known-paper.md` |
| 用户想重新搜索、缩小范围 | 返回 Step 1（refine） |
| 用户想精读 | `deep-analyze-paper.md` |

---

## 禁止

- 不要在搜索结果中替用户决定读哪篇
- 不要在搜索阶段读全文
- 不要对零结果硬猜路径
- 不要主动并行 `search + retrieve`——只走 primary → fallback 顺序
