---
name: logging
description: >
  Work and reading log management. Triggered by:
  "logging work", "logging read",
  "做工作记录", "做阅读记录", "做working-log", "做reading-log",
  "写工作日志", "写阅读日志", "记录工作", "记录阅读",
  "写日志", "记一下", "总结一下这个会话",
  "记录决策", "记一下工作过程", "写工作总结",
  "这节的结论是什么", "这段有什么值得记录的".
source: paperforge
---

# Logging

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

## 2. Routing — 判断用户要什么

根据用户说的内容确定走哪个分支：

| 用户说                                      | 走分支   |
| ------------------------------------------- | -------- |
| "记录阅读" "reading log" "做阅读记录" "这段有什么值得记的" "读完了记一下" "刚读了一段记一下" "有没有什么值得记的" "把这段记下来" | **reading** |
| "工作记录" "working log" "总结会话" "记一下工作过程" "写工作总结" "记录决策" "logging work" | **working** |
| "写日志" "记录一下" "记一下" 不清楚哪个      | **先问用户** |

## 3. reading 分支 — 记录单条阅读笔记

调用条件：用户读完一个段落/章节后要记录。

动作：
1. 确认 `$VAULT` 和 `$PYTHON`
2. 确定 zotero_key（从上下文或 formal note 中获取）
3. 提取：
   - **section**: 文献中的位置 (Discussion P12, Results Fig.3)
   - **excerpt**: 逐字引用的原文关键句
   - **usage**: 这个信息支持当前写作的哪个论点
   - **note**: 交叉验证/矛盾/注意事项 (optional)
4. 给用户展示确认后再执行：
   ```
   $PYTHON -m paperforge --vault $VAULT reading-log --write KEY \
       --section "..." --excerpt "..." --usage "..." --note "..."
   ```
5. 确认写入成功

## 4. working 分支 — 会话总结写入 working-log

调用条件：会话结束前/用户要求记录工作过程。

动作：
1. 回顾本次会话中所有关键节点:
   - 用户纠正了什么
   - 方案怎么变的
   - 有什么弯路和教训
   - 可复用的方法论
2. 按以下格式生成 markdown，给用户确认：

   ```
   ## YYYY-MM-DD — 小节名

   ### 核心决策
   - 做了什么、为什么

   ### 弯路与修正
   - 错误方向 → 用户纠正 → 最终方案

   ### 可复用方法论
   - 本段的 pattern

   ### 待办
   - [ ] ...
   ```

3. 用户确认后，询问目标 project 目录路径
4. 追加到 `Project/<project>/working-log.md`（文件不存在则新建）
5. 确认写入成功

---

## 5. Export — 导出 reading-log

用户说 "导出阅读日志"：

```bash
$PYTHON -m paperforge --vault $VAULT reading-log --output <path> [--since DATE]
```

导出为 markdown 文件。如果用户没指定路径，询问。
