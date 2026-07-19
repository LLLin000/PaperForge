# /pf-end

## Purpose

结束当前论文 Q&A 并保存讨论记录。需要用户**显式要求**时才执行，不自动触发。

## Trigger

用户说以下任一关键词时执行（所有平台通用）：
- `保存` / `记录` / `保存记录`
- `结束` / `完成`
- `save discussion` / `save` / `done`

或显式命令：
- `/pf-end <zotero_key>`

如果未指定 key，则使用当前已加载的论文 key。

## Save Format

```json
{
  "question": "用户的问题",
  "answer": "Agent 的回答",
  "source": "user_question",
  "timestamp": "2026-05-06T12:00:00+08:00"
}
```

## Command

```bash
python -m paperforge.worker.discussion record <ZOTERO_KEY> \
    --vault "<VAULT_PATH>" \
    --agent pf-paper \
    --model "<MODEL_NAME>" \
    --qa-pairs '<JSON_ARRAY>'
```

## Verification

CLI 返回 `{"status": "ok", ...}`。失败则重试。

## See Also

- [pf-paper](pf-paper.md)
- [pf-deep](pf-deep.md)
