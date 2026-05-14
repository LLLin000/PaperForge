# paper-search

从文献库中按条件检索文献，返回候选清单及每篇的可用状态。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`、`$LIT_DIR`）

---

## 步骤

### Step 1: 解析用户搜索意图

提取以下信息（缺什么就问用户）：
- **搜索词**：关键词、作者名、年份
- **范围**：domain（如"骨科"）、collection（如"DC"）、不指定=全库
- **过滤条件**：OCR 状态（done/pending）、年份范围（--year-from/--year-to）、lifecycle

### Step 2: 执行搜索

```bash
$PYTHON -m paperforge search <query> --json --vault "$VAULT" --limit 15 \
    [--domain "<domain>"] \
    [--year-from <N>] [--year-to <N>] \
    [--ocr <done|pending>] \
    [--lifecycle <active|archived>]
```

返回 JSON 结构：
```json
{
  "ok": true,
  "data": {
    "query": "<query>",
    "matches": [
      {
        "zotero_key": "ABC12345",
        "citation_key": "...",
        "title": "...",
        "year": "2024",
        "first_author": "Smith",
        "domain": "...",
        "collection_path": "...",
        "ocr_status": "done",
        "deep_reading_status": "pending",
        "lifecycle": "active",
        "has_pdf": true,
        "rank": "..."
      }
    ],
    "count": 5
  }
}
```

- 如果 `ok: false` → 报告 `error.message`，问用户是否换搜索词
- 如果 `data.count == 0` → 告知用户无结果，建议换词或扩大范围
- 如果 `data.count > 0` → 进入 Step 3

### Step 3: 逐个确认状态（paper-context 原子）

对每个 match，调 `paper-context` 获取更详细的可读状态：

```bash
$PYTHON -m paperforge paper-context <zotero_key> --json --vault "$VAULT"
```

目的：拿到 `ocr_status`、`prior_notes` 数量、`analyze` 状态，帮助用户判断哪些可以直接读。

### Step 4: 展示候选清单

格式（每条一行）：

```
找到 N 篇匹配 "<query>"：

[1] ABC12345 | Smith 2024 | Title Here | 骨科 | OCR: done | 精读: pending | 阅读笔记: 3
[2] DEF67890 | Jones 2023 | Title Here | 骨科 | OCR: done | 精读: done   | 阅读笔记: 0
[3] GHI11111 | Wang 2022  | Title Here | 骨科 | OCR: pending |           | 阅读笔记: 0
```

关键字段：zotero_key, first_author, year, title, ocr_status, deep_reading_status, prior_notes 数量

### Step 5: 等用户选择后续操作

展示候选后不要自己决定下一步。等用户说：
- "读一下 [1]" → 路由到 paper-qa.md
- "精读 [2]" → 路由到 deep-reading.md
- "记一下 [1]" → 路由到 reading-log.md
- "缩小范围"/"refine" → 回到 Step 1，加更多过滤条件

---

## 禁止

- 不要在搜索结果中替用户决定读哪篇
- 不要在搜索阶段读全文
- 不要对 0 结果硬猜路径
