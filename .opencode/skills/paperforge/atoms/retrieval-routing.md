# retrieval-routing

**Agent 检索决策的唯一事实源。三条线性路由,无状态机。**

这个 atom 定义 Agent 如何调用 PaperForge 检索后端。目标是:路由选择由协议
决定,Agent 只负责复制命令、读点名字段、按冻结规则回退。

> 本协议取代旧版 Planner Protocol / Safe Executor / Exactly-One-Fallback
> 状态机。`query-plan` 不再是任何路由的第一步——它只是 optional diagnostic,
> 不属于 Route A/B/C。

---

## 1. 路由选择(三分支)

每次检索只选一条路由。从第一条开始,匹配即停:

```text
Route A — 已知论文(明确 title / DOI / Zotero key)
         → 见 §2
Route B — 已知论文内的某个段落/概念/参数
         → 见 §3
Route C — 模糊问题 / 不知道哪篇 / 跨库找证据
         → 见 §4
```

判断规则:

| 用户输入 | 路由 |
|---------|------|
| "看这篇:Machine Learning in Hypertrophic Cardiomyopathy" | A |
| "DOI 10.1016/j.jcmg.2024.04.013 这篇" | A |
| "KI6EB48K" | A |
| "这篇的 RFE 是怎么做的" | B |
| "这篇用了多少 Hz" | B |
| "找 PTOA 相关的文献" | C |
| "哪些论文用了 RFE 做特征选择" | C |

## 2. Route A — 已知论文

固定命令链,线性执行:

```text
1. 用户给了 exact identifier(zotero key / DOI / citation key)?
   YES → 直接 paper-context(见 step 3),不做任何 search

2. 只有 title / author+year:
   跑 exact search(命令见下)

   matches 非空 → 取第一个 → step 3
   matches 空:
     → 用户输入里还有另一个明确 identifier(如 title + DOI 都有)?
        用那个 identifier 再 exact search 一次
     → 否则 STOP,报告 "paper not found"
```

**硬规则:exact identifier(zotero key / DOI / citation key)禁止经过
search/retrieve** — `paper-context` 直接解析(与 zotero key 同级)。
title search 0 结果 → retrieve 同样禁止(semantic retrieve 不承担
identity resolution)。

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <IDENTIFIER> --json
```

READ ONLY:`data.paper.zotero_key` / `data.paper.title`

只有 title / author+year 才用 search:

3. 取上下文:

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --json
```

READ ONLY:
```text
data.paper.title
data.paper.fulltext_path
data.paper.pdf_path
```

不读 `data.title`、不读其他嵌套字段。需要元数据展示时也从这三项派生
(`data.paper.year` / `data.paper.journal` / `data.paper.first_author`
可选)。

4. 读正文:`molecules/pre-read.md` Step 3。

## 3. Route B — 已知论文内找段落

先定位论文(Route A),然后:

```text
1. 本地读文(一个命令,协议处理路径):
   paperforge --vault "$VAULT" read <KEY> --find "<词>" --json

   data.status:
   - matched → 用 data.matches[] 回答(source + line/page),完成
   - no_match + 语义概念问题 → retrieve 一次(见下)
   - no_match + 明确术语 → 报告未检索到,停止
   - no_readable_source → 报告 no readable source,停止

2. retrieve 仅用于"原文可能不用该术语"的语义概念:
   paperforge --vault "$VAULT" retrieve "<问题>" --paper <KEY> --json
   之后 STOP,不二次 fallback。
```

`read --find` 是本地读文的唯一入口(fulltext + canonical PDF,auto)。
`retrieve` 是 semantic fallback,不是默认 reader。

## 4. Route C — 模糊 / 跨库

```text
1. search:
   $PYTHON -m paperforge --vault "$VAULT" search "<关键词>" --limit 10 --json

   matches 非空 → 展示候选 → 用户选择后走 Route A
   matches 空 → step 2

2. retrieve 一次:
   $PYTHON -m paperforge --vault "$VAULT" retrieve "<关键词>" --json

   → 展示结果,标记 "semantic match,非精确词面"
   → 无论结果如何,到此停止

3. 不二次 fallback。
```

## 5. 冻结规则

- **每阶段最多 1 次 fallback**,fallback 后即停止,不再换策略。
- **禁止第四条检索策略**:除 search / paper-context / retrieve / `read --find`
  之外,不得发明新工具或新命令(不手写 grep、不手写 PyMuPDF、不做 storage
  discovery)。
- `scope=paper`(Route B)时**永远不扩大到 library**。
- `query-plan` 仅在用户明确要求诊断/推荐时才运行,其结果不改变以上路由。

## 6. Object evidence(图表)最小解析

收到 `source_kind=object` 的命中时:

1. 读 `object_label` + `caption_text`。
2. caption 已直接回答 → 用,标注 "图表 caption 信息",不补查。
3. caption 不足且用户需要作者解释 → 在同一论文内跑一次 Route B 的
   `retrieve --paper KEY` 补正文。
4. 找不到正文引用 → 只展示 caption,说明"未检索到正文中的直接讨论"。

不重复补查同一 object_label。

## 7. 命令速查

| 命令 | 用途 | 何时用 |
|------|------|--------|
| `search "<词>" --limit N --json` | 元数据定位 | Route A step 2 / Route C step 1 |
| `paper-context <KEY> --json` | canonical 上下文 | Route A step 3 / pre-read Step 2 |
| `read <KEY> --find "<词>" --json` | 本地读文(fulltext+PDF) | Route B / pre-read Step 3 |
| `retrieve "<问题>" [--paper KEY] --json` | 语义检索 | Route B 语义兜底 / Route C step 2 |
