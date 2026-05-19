# write-project-log

记录会话/项目日志到 `project-log.jsonl`，包含决策、弯路、待办等。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 project 名称
- 对话上下文中已有会话内容可回顾

---

## Schema

```json
{
  "id": "plog_20260519_001",
  "project": "综述写作",
  "date": "2026-05-19",
  "type": "session_summary",
  "title": "DC 段参数窗审计",
  "decisions": ["做了 X，因为 Y"],
  "detours": [
    {
      "wrong": "错误方向",
      "correction": "用户如何纠正",
      "resolution": "最终方案"
    }
  ],
  "reusable": ["可复用的方法论或教训"],
  "todos": [
    {"content": "待办事项", "done": false}
  ],
  "related_papers": ["ABC12345"],
  "tags": ["DC", "参数窗", "审计"],
  "agent": "opencode"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | 是 | 自动生成 `plog_YYYYMMDD_NNN` |
| `project` | 是 | 项目名 |
| `date` | 是 | YYYY-MM-DD |
| `type` | 是 | `session_summary` / `decision` / `correction` / `milestone` / `note` |
| `title` | 是 | 简短标题 |
| `decisions` | 否 | 核心决策列表 |
| `detours` | 否 | 弯路与修正记录 |
| `reusable` | 否 | 可复用方法论 |
| `todos` | 否 | 待办事项 |
| `related_papers` | 否 | 相关 Zotero keys |
| `tags` | 否 | 分类标签 |
| `agent` | 否 | 记录者 |

---

## 步骤

### Step 1: 确定 project 和 type

从上下文获取。如果用户未指定 project，询问。

type 参考：

| type | 使用场景 |
|------|---------|
| `session_summary` | 会话结束时的总结 |
| `decision` | 单独记录一个重要决策 |
| `correction` | 用户纠正了某个方向 |
| `milestone` | 项目里程碑 |
| `note` | 一般研究笔记 |

### Step 2: 回顾本次会话

提取以下内容：
- **做了什么**（核心决策及其原因）
- **用户纠正了什么**（弯路与修正）
- **有什么可复用的发现**
- **待办事项**

### Step 3: 展示确认

```
即将记录:
  日期: 2026-05-19
  类型: session_summary
  标题: DC 段参数窗审计完成
  决策:
    - 限定参数窗为 100Hz-1kHz
  弯路:
    - 把推断当文献事实 → 用户要求逐句审计 → 5 处修正
  可复用:
    - 写完必须逐句过 source

确认写入？(y/n)
```

### Step 4: 写入

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --write \
    --project "<project>" \
    --payload '<payload>'
```

payload 为完整 JSON 对象（单行序列化）。

返回 `ok: true` → 写入成功；`ok: false` → 报错重试。

### Step 5: 确认渲染

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --render --project "<project>"
```

输出到 `Resources/Projects/<project>/project-log.md`。

---

## 禁止

- 不要在用户确认前写入
- 不要只写"做了什么"而没有"弯路"和"可复用"部分

---

## 参考

详情请看 `workflows/project-log.md`。
