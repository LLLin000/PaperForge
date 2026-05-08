---
name: pf-end
description: Save the paper Q&A discussion record. Triggered when user says "保存" "结束" "save" or types $pf-end. Summarizes all Q&A pairs and writes them to the paper's ai/discussion directory via the discussion module.
allowed-tools: [Read, Bash]
---

# <prefix>pf-end

## Purpose

结束当前论文对话并保存讨论记录。需要用户**显式要求**时才执行，不自动触发。

1. 汇总本次对话中所有 Q&A 对
2. 通过 `discussion.record_session()` 写入论文工作区的 `ai/` 目录
3. 告知用户记录已保存

## Trigger

用户说以下任一关键词时执行（全平台通用）：
- `保存` / `记录` / `保存记录`
- `结束` / `完成`
- `save discussion` / `save` / `done`

也可以显式指定 key：
- `{prefix}pf-end <zotero_key>`（OpenCode）
- `保存 <zotero_key>`（全平台）

如果未指定 key，则使用当前已加载的论文 key。

## Save Format

将会话期间的所有 Q&A 序列化为 JSON 数组：

```json
{
  "question": "用户的问题",
  "answer": "Agent 的回答",
  "source": "user_question",
  "timestamp": "2026-05-06T12:00:00+08:00"
}
```

`source` 为 `"user_question"`（用户提问）或 `"agent_analysis"`（Agent 主动分析）。

## Command

```bash
python -m paperforge.worker.discussion record <ZOTERO_KEY> \
    --vault "<VAULT_PATH>" \
    --agent pf-paper \
    --model "<MODEL_NAME>" \
    --qa-pairs '<JSON_ARRAY>'
```

## Verification

CLI 返回：
```json
{"status": "ok", "json_path": "Literature/{domain}/{key} - {title}/ai/discussion.json", "md_path": "..."}
```

如果 `status` 为 `"error"`，记录错误信息并重试，不要跳过。

## See Also

- [pf-paper](pf-paper.md) — 论文 Q&A 工作台
- [pf-deep](pf-deep.md) — 完整三阶段精读
