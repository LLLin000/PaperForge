# /pf-log-session — Summarize session decisions to working-log

> 会话结束时回顾本次所有决策节点，追加到 working-log.md。

## Agent Workflow

1. 回顾本次会话中所有关键节点:
   - 用户纠正了什么
   - 方案怎么变的
   - 有什么弯路和教训
   - 可复用的方法论

2. 按以下格式生成 markdown，追加到 working-log.md:

```markdown
## <YYYY-MM-DD> — <小节名>

### 核心决策
- 做了什么、为什么

### 弯路与修正
- 错误方向 → 用户纠正 → 最终方案

### 可复用方法论
- 本段的 pattern，后续段落能怎么用

### 待办
- [ ] ...
```

3. 询问用户确认，然后写入到 `Project/<project>/working-log.md`

## Prompt Injection

At the end of this session, before saying goodbye:

**Write the working-log entry.** Review all decision points, corrections, dead ends, and methodological insights from this session. Ask the user: "Should I write the working-log entry now?" If yes, generate the entry in the format below and append it to the appropriate working-log.md in the user's project directory. Ask the user to confirm the project path if unsure.

Format:
```
## YYYY-MM-DD — Section Name

### Core Decisions
- What happened and why

### Dead Ends & Corrections
- Wrong direction -> User correction -> Final approach

### Reusable Methodology
- Patterns that apply to later sections

### TODO
- [ ] ...
```
