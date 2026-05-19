# discover-papers

从文献库中发现和检索论文，返回候选清单（candidate list）。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`、`$LIT_DIR`）

---

## 步骤

### Step 1: 解析用户搜索意图

提取以下信息（缺什么就问用户）：
- **搜索词**：关键词、作者名、年份
- **范围**：domain（如"骨科"）、不指定=全库
- **过滤条件**：OCR 状态、年份范围（`--year-from`/`--year-to`）、lifecycle

### Step 2: 执行元数据搜索（`paperforge search`）

```bash
$PYTHON -m paperforge --vault "$VAULT" search <query> --json --limit 15 \
    [--domain "<domain>"] \
    [--year-from <N>] [--year-to <N>] \
    [--ocr <done|pending|failed|processing>] \
    [--lifecycle <indexed|pdf_ready|fulltext_ready|deep_read_done>]
```

返回 JSON 结构（候选论文清单）：
```json
{
  "ok": true,
  "data": {
    "query": "<query>",
    "matches": [
      {
        "zotero_key": "ABC12345",
        "title": "论文标题",
        "year": "2024",
        "first_author": "Smith",
        "domain": "骨科",
        "ocr_status": "done",
        "deep_reading_status": "pending",
        "lifecycle": "pdf_ready",
        "has_pdf": true
      }
    ],
    "count": 5
  }
}
```

- 如果 `ok: false` → 报告 `error.message`，问用户是否换搜索词
- 如果 `data.count == 0` → 告知用户无结果，建议换词或扩大范围
- 如果 `data.count > 0` → 进入 Step 3

### Step 3: Top-hit 富化（`paperforge paper-context`）

对每个 match，调 `paper-context` 获取更详细的可读状态：

```bash
$PYTHON -m paperforge --vault "$VAULT" paper-context <zotero_key> --json
```

目的：拿到 `ocr_status`、`prior_notes` 数量、`analyze` 状态，帮助用户判断哪些可以直接读。

### Step 4: 展示候选清单

格式（每条一行）：

```
找到 N 篇匹配 "<query>"：

[1] ABC12345 | Smith 2024 | 论文标题 | 骨科 | OCR: done | 精读: pending | 阅读笔记: 3
[2] DEF67890 | Jones 2023 | 论文标题 | 骨科 | OCR: done | 精读: done   | 阅读笔记: 0
[3] GHI11111 | Wang 2022  | 论文标题 | 骨科 | OCR: pending |           | 阅读笔记: 0
```

关键字段：`zotero_key`、`first_author`、`year`、`title`、`domain`、`ocr_status`、`deep_reading_status`

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
