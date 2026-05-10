# 保存讨论记录

将 paper-qa 会话中的 Q&A 记录持久化到论文工作区。

---

## 触发条件

- 用户显式说 "保存"、"保存记录"、"结束"、"完成讨论"、"save"
- 或显式输入 `/pf-end`
- 不要自动触发

---

## 执行

### Step 1: 收集 Q&A 对

汇总本次 paper-qa 会话中所有 Q&A，序列化为 JSON 数组：

```json
[
  {
    "question": "用户的问题",
    "answer": "Agent 的回答",
    "source": "user_question",
    "timestamp": "2026-05-10T12:00:00+08:00"
  }
]
```

`source` 为 `"user_question"`（用户提问）或 `"agent_analysis"`（Agent 主动分析）。

### Step 2: 调用 discussion 模块

```bash
python -m paperforge.worker.discussion record <ZOTERO_KEY> \
    --vault . \
    --agent pf-paper \
    --model "<CURRENT_MODEL>" \
    --qa-pairs '<JSON_ARRAY>'
```

### Step 3: 确认结果

CLI 返回 `{"status": "ok", ...}` → 告知用户记录已保存。

返回 `{"status": "error"}` → 记录错误，重试一次。仍失败则告知用户。

---

## 注意事项

- 仅 paper-qa 会话需要记录。deep-reading 的内容直接写入 formal note，不需要通过本文件。
- 如果无法从 formal-library.json 找到论文 domain/title，记录失败不应影响用户使用。
