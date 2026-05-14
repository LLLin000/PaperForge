# project-log

> **Scope:** Record what happened this session — decisions, detours, todos.
> For reusable cross-project methods, use methodology workflow instead.

记录研究项目的会话总结、决策、弯路修正和方法论提取。
Agent 按 JSON schema 写入 project-log.jsonl。
系统自动渲染对应项目的 project-log.md。

---

## 前置条件

- bootstrap 已完成（有 `$VAULT`、`$PYTHON`）
- 已知 project 名称

---

## 项目日志 JSON Schema

```json
{
  "id": "plog_<YYYYMMDD>_<序号>",
  "project": "综述写作",
  "date": "2026-05-14",
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

| 字段             | 必填 | 说明                                        |
| ---------------- | ---- | ------------------------------------------- |
| `id`             | 是   | 自动生成 `plog_YYYYMMDD_NNN`                |
| `project`        | 是   | 项目名                                      |
| `date`           | 是   | YYYY-MM-DD                                  |
| `type`           | 是   | `session_summary` / `decision` / `correction` / `milestone` / `note` |
| `title`          | 是   | 本条目的简短标题                            |
| `decisions`      | 否   | 核心决策列表                                |
| `detours`        | 否   | 弯路与修正记录                              |
| `reusable`       | 否   | 可复用的方法论或教训                        |
| `todos`          | 否   | 待办事项                                    |
| `related_papers` | 否   | 相关 Zotero keys                            |
| `tags`           | 否   | 分类标签                                    |
| `agent`          | 否   | 记录者                                      |

---

## 步骤

### Step 1: 确定 project

从上下文获取。如果用户未指定，询问。

### Step 2: 回顾本次会话

回顾以下内容：
- 做了什么（核心决策）
- 用户纠正了什么（弯路与修正）
- 有什么可复用的方法论或教训
- 待办事项

### Step 3: 按 Schema 组织内容，展示确认

展示给用户确认后再写入：

```
即将记录到 Project/综述写作/project-log.md:
  日期: 2026-05-14
  类型: session_summary
  标题: DC 段参数窗审计完成
  决策:
    - 限定参数窗为 100Hz-1kHz
    - 移除 AC vs DC 对比段落
  弯路:
    - 把推断当文献事实 → 用户要求逐句审计 → 5 处修正
  可复用:
    - 写完必须逐句过 source，区分"文献说了什么"和"我推断什么"

确认写入？(y/n)
```

### Step 4: 写入（Atom）

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --write \
    --project "<project>" \
    --payload '<payload>'
```

- 返回 `ok: true` → 确认写入成功。**自动渲染对应项目 markdown。**
- 返回 `ok: false` → 报告错误，重试一次

### Step 5: 确认渲染

```bash
$PYTHON -m paperforge --vault "$VAULT" project-log --render --project "<project>"
```

输出到 `Project/<project>/project-log.md`。

---

## type 参考

| type              | 使用场景                       |
| ----------------- | ------------------------------ |
| `session_summary` | 会话结束时的总结               |
| `decision`        | 单独记录一个重要决策           |
| `correction`      | 用户纠正了某个方向             |
| `milestone`       | 项目里程碑                     |
| `note`            | 一般研究笔记                   |

---

## 禁止

- 不要在用户确认前写入
- 不要只写"做了什么"而没有"弯路与修正"和"可复用方法论"
