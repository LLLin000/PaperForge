# Phase 33: Deep-Reading Dashboard Rendering - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 33-deep-reading-dashboard-rendering
**Areas discussed:** Pass 1 extraction, Status bar, AI Q&A display, Layout

---

## Pass 1 Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| 一级标题解析 | 查找 `## Pass 1` 和 `## Pass 2` 之间内容 | |
| 标记词解析 | 查找 `**一句话总览**` 等标记后的文本 | ✓ |

**User's choice:** 标记词解析 — 灵活，匹配不同写作风格

**Follow-up — Specific markers:**
- User provided sample content showing `**一句话总览**` + paragraph + `###` sub-sections
- Decision: Extract all content from the matched marker onward, including `###` sub-sections
- Priority order: `**一句话总览**` → `**Pass 1**` → `**文章摘要**`

---

## Status Bar

| Option | Description | Selected |
|--------|-------------|----------|
| 徽章行 | 横向排列徽章 | |
| 信息卡片 | 纵向列表，带图标和文字 | ✓ |

**User's choice:** 信息卡片 — 与 per-paper health matrix 风格一致

---

## AI Q&A Display

| Option | Description | Selected |
|--------|-------------|----------|
| 最近 5 条问答 | 简单列表，最近优先 | |
| 按会话分组 | 每个 session 可展开/折叠 | ✓ |

**User's choice:** 按会话分组 — 完整展示每次讨论

**Follow-up — Q&A format:**
| Option | Description | Selected |
|--------|-------------|----------|
| 问题:... 解答:... | 两行文字格式 | |
| 对话气泡 | 不同颜色背景，类似聊天界面 | ✓ |

**User's choice:** 对话气泡 — 问题/解答不同颜色

---

## Layout

| Option | Description | Selected |
|--------|-------------|----------|
| 纵向堆叠+卡片 | 三个卡片上下排列 | ✓ |
| 可折叠面板 | 全部可折叠 | |

**User's choice:** 纵向堆叠，AI 问答默认折叠，状态栏和 Pass 1 默认展开

---

## Deferred Ideas

None — discussion stayed within phase scope
