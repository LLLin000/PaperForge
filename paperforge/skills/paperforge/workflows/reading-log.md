# reading-log

记录单条阅读笔记。Agent 将用户确认的信息按 JSON schema 写入 reading-log.jsonl。
系统自动渲染对应项目的 reading-log.md（给人看）并导入 paperforge.db（可搜索）。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 paper_id（zotero_key）

---

## 阅读笔记 JSON Schema

每条阅读笔记必须包含以下字段：

```json
{
  "id": "rln_<YYYYMMDD>_<序号>",
  "paper_id": "ABC12345",
  "project": "综述写作",
  "section": "Results Fig.3",
  "excerpt": "原文关键句（逐字引用）",
  "context": "包含 excerpt 的完整段落（供后续回原文复核时定位）",
  "usage": "这个信息在当前写作中的用途",
  "note": "注意事项 / 待核查 / 可能矛盾",
  "tags": ["PEMF", "dose-response"],
  "verified": false
}
```

| 字段      | 必填 | 说明                                                     |
| --------- | ---- | -------------------------------------------------------- |
| `id`      | 是   | 自动生成，格式 `rln_YYYYMMDD_NNN`                        |
| `paper_id` | 是   | Zotero key（8位大写字母数字）                            |
| `project` | 否   | 关联的研究项目                                           |
| `section` | 是   | 文献中的位置（如 "Results Fig.3"、"Discussion P12"）     |
| `excerpt` | 是   | 逐字引用的原文关键句                                     |
| `context` | 是   | 包含 excerpt 的完整段落，供复核定位                      |
| `usage`   | 是   | 这个信息在当前工作（写作/研究）中的用途                  |
| `note`    | 否   | 交叉验证、矛盾、待核查事项                               |
| `tags`    | 否   | 分类标签，供横切检索                                     |
| `verified` | 否   | 默认 false。Agent 回原文复核后应更新为 true              |

---

## 步骤

### Step 1: 确认 paper_id 和 project

从上下文获取 zotero_key。如果用户未指定 project，询问或留空。

### Step 2: Agent 按 Schema 提取内容

从对话上下文中提取 `section`、`excerpt`、`context`、`usage`、`note`、`tags`。

**excerpt vs context 的区别：**
- `excerpt`：你关注的那一句（逐字引用）
- `context`：包含这句的完整段落（3-5 句），让以后的人不翻原文也能理解语境

### Step 3: 展示确认

先展示给用户确认，不要直接写入：

```
即将记录:
  文献: ABC12345 | Smith 2024
  位置: Results Fig.3
  原文: "..."
  用途: 支撑 PEMF 基质合成的论证
  备注: 需核查是否对 DNA 归一化了
  项目: 综述写作
  标签: PEMF, GAG
  段落语境: "..."

确认写入？(y/n)
```

### Step 4: 写入（Atom）

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

- 返回 `ok: true` → 确认写入成功。**写入后自动渲染对应项目的 markdown。**
- 返回 `ok: false` → 报告错误，重试一次

### Step 5: 确认渲染

```bash
$PYTHON -m paperforge --vault "$VAULT" reading-log --render --project "<project>"
```

输出到 `Project/<project>/reading-log.md`。

---

## 禁止

- 不要在用户确认前写入
- 不要把推断当作 `excerpt`（必须是原文逐字引用）
- 不要让 `context` 为空（必须是完整段落）
