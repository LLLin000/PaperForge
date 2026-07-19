# write-reading-log-jsonl

向 `reading-log.jsonl` 追加单条结构化阅读条目。

**定位：结构化索引层**——简短、可搜索、机器可解析。每条条文对应论文中的一句引用/发现。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 `paper_id`（zotero_key）
- 上下文中有待记录的 excerpt 和相关信息

---

## Schema

```json
{
  "id": "rln_20260519_001",
  "paper_id": "ABC12345",
  "project": "综述写作",
  "section": "Results Fig.3",
  "excerpt": "原文关键句（逐字引用）",
  "context": "包含 excerpt 的完整段落",
  "usage": "这个信息在写作中的用途",
  "note": "注意事项 / 待核查",
  "tags": ["PEMF", "dose-response"],
  "verified": false
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 自动生成 `rln_YYYYMMDD_NNN` |
| `paper_id` | 是 | Zotero key（8位大写） |
| `project` | 否 | 关联的研究项目 |
| `section` | 是 | 文献位置 |
| `excerpt` | 是 | 逐字引用原文 |
| `context` | 是 | 完整段落供复核定位 |
| `usage` | 是 | 在写作中的用途 |
| `note` | 否 | 待核查事项 |
| `tags` | 否 | 分类标签 |
| `verified` | 否 | 默认 false |

---

## 步骤

### Step 1: 收集必填字段

从对话上下文提取：`paper_id`、`section`、`excerpt`、`context`、`usage`。

### Step 2: 生成 id

格式：`rln_<YYYYMMDD>_<3位序号>`（序号从上下文已存在的条数推断）

### Step 3: 展示确认

```
即将记录:
  文献: ABC12345 | Smith 2024
  位置: Results Fig.3
  原文: "..."
  用途: 支撑 PEMF 基质合成的论证
  项目: 综述写作
  标签: PEMF, GAG

确认写入？(y/n)
```

### Step 4: 写入

```bash
$PYTHON -m paperforge --vault "$VAULT" reading-log --write <paper_id> \
    --section "<section>" \
    --excerpt "<excerpt>" \
    --context "<context>" \
    --usage "<usage>" \
    --note "<note>" \
    --project "<project>" \
    --tags "<tag1>,<tag2>"
```

返回 `ok: true` → 写入成功；`ok: false` → 报错重试一次。

### Step 5: 触发渲染

```bash
$PYTHON -m paperforge --vault "$VAULT" reading-log --render --project "<project>"
```

输出到 `Resources/Projects/<project>/reading-log.md`。

---

## 禁止

- 不要在用户确认前写入
- `excerpt` 必须是原文逐字引用，不能是推断或改写
- `context` 不能为空

---

## 参考

详情请看本 atom 顶部的确认模板部分。
