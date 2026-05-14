# /pf-log-reading — Record a reading note

> 读完当前段落或章节后自动记录到 paperforge.db 的 paper_events 表。

## Agent Workflow

1. 确定 zotero_key (从上下文或 formal note 中获取)
2. 提取以下信息:
   - **section**: 文献中的位置 (e.g. "Discussion P12", "Results Fig.3")
   - **excerpt**: 逐字引用的原文关键句
   - **usage**: 这个信息支持当前写作的哪个论点
   - **note**: 任何交叉验证/矛盾/注意事项 (optional)

3. 执行:
```bash
paperforge reading-log --write <KEY> \
    --section "Discussion P12" \
    --excerpt "the fundamental disjunction between materials science and biology" \
    --usage "F 段 gap 论点" \
    --note "与 DDGMQ7RW 独立诊断同一问题"
```

## Prompt Injection

After reading a section or paragraph from a paper:

**Record a reading note.** Determine the zotero_key of the paper you just read. Extract the section name (e.g. "Discussion P12", "Results Fig.3"), a verbatim excerpt of the key sentence, how this supports the current writing task, and any cross-validation notes. Then run:

```
paperforge --vault {vault_path} reading-log --write KEY --section "..." --excerpt "..." --usage "..." --note "..."
```

If the user's vault path is unknown, ask before running.
