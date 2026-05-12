---
name: literature-logging
description: >
  Literature reading and working log management. Triggered by:
  /pf-log-reading /pf-log-session,
  "记录阅读", "记录一下", "写日志", "读完了",
  "总结会话", "写工作总结", "写working log",
  "记一下工作过程", "记录决策".
---

# Literature Logging

---

## 1. Bootstrap — 必须先执行

跑这个脚本：

```
python $SKILL_DIR/scripts/pf_bootstrap.py
```

返回 JSON。记住以下变量：

| 变量        | 来自 JSON 的         | 用于                                          |
| ----------- | -------------------- | --------------------------------------------- |
| `$VAULT`      | `vault_root`           | 所有 `--vault` 参数                             |
| `$PYTHON`     | `python_candidate`     | 所有 cli 调用                                   |

如果 `ok: false` → 报告 `error` 给用户，**停止**。

---

## 2. State Check — 检查当前日志状态

```
$PYTHON -m paperforge --vault $VAULT reading-log --json
```

展示：已有多少条 reading notes。如果 0 条，告知用户："还没有阅读记录，读完文献后使用 /pf-log-reading 记录。"

---

## 3. Routing

### /pf-log-reading — 记录单条阅读笔记

**调用条件**: 用户在阅读文献过程中，或读完一个段落/章节后

**Agent 行为**:
1. 确认 zotero_key（从上下文或 formal note 中获取）
2. 提取以下信息:
   - **section**: 文献中的位置 (e.g. "Discussion P12", "Results Fig.3")
   - **excerpt**: 逐字引用的原文关键句
   - **usage**: 这个信息支持当前写作的哪个论点
   - **note**: 任何交叉验证/矛盾/注意事项 (optional)
3. 询问用户确认，然后执行:
```bash
$PYTHON -m paperforge --vault $VAULT reading-log --write KEY \
    --section "SECTION" --excerpt "EXCERPT" \
    --usage "USAGE" --note "NOTE"
```
4. 确认写入成功

### /pf-log-session — 会话总结写入 working-log

**调用条件**: 写作/研究会话结束前，用户说 "写日志" 或 "/pf-log-session"

**Agent 行为**:
1. 回顾本次会话中所有关键节点:
   - 用户纠正了什么
   - 方案怎么变的
   - 有什么弯路和教训
   - 可复用的方法论
2. 按以下格式生成 markdown:

```
## <YYYY-MM-DD> — <小节名>

### 核心决策
- 做了什么、为什么

### 弯路与修正
- 错误方向 → 用户纠正 → 最终方案

### 可复用方法论
- 本段的 pattern

### 待办
- [ ] ...
```

3. 展示给用户确认
4. 询问目标 project 目录中的 working-log.md 路径
5. 如果文件不存在：新建并写入
6. 如果文件存在：先读旧内容，在文件末尾追加 `\n---\n` 分隔线，再追加新内容
7. 确认写入成功

### Auto — 静默记录

用户没有显式说 "记录" 但 agent 读了一篇论文的某段时，agent 可以**主动问**:

```
我读了 LQZ2FWIW Discussion P12 关于 magnetoelectric 分类的内容。
要记录到 reading-log 吗？(/pf-log-reading)
```

不要擅自记录——必须征得用户同意。

---

## 4. Export — 导出 reading-log

用户说 "导出阅读日志" 或 "/pf-log-export"：

```bash
$PYTHON -m paperforge --vault $VAULT reading-log --output <path> [--since DATE]
```

导出为 markdown 文件。如果用户没指定路径，询问。
