# Phase 32: Deep-Reading Mode Detection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 32-deep-reading-mode-detection
**Areas discussed:** Detection boundary, Key resolution, Identity guard, Edge cases

---

## Detection Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| 仅检测文件名 | 只要文件名是 deep-reading.md 就进入 deep-reading 模式 | |
| 文件名+目录结构 | 文件名是 deep-reading.md 且父目录符合 {key} - {Title} 模式 | ✓ |

**User's choice:** 文件名+目录结构 — 更精确，避免误触发

---

## Key Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| 从文件名解析 | 从父目录名提取 {key} - {Title} 中的 8 位 key | |
| 从 frontmatter | deep-reading.md 的 frontmatter 中读取 zotero_key | ✓ |

**User's choice:** 从 frontmatter — 与现有 per-paper 模式一致

---

## Identity Guard

| Option | Description | Selected |
|--------|-------------|----------|
| 模式+文件路径双重检查 | mode 和文件路径都变了才重建 dashboard | ✓ |
| 仅模式检查 | 沿用当前逻辑只检查 mode 字符串 | |

**User's choice:** 模式+文件路径双重检查 — 解决 active-leaf-change double-fire 问题

---

## Edge Cases

| Option | Description | Selected |
|--------|-------------|----------|
| 显示 global 模式 | 文件名匹配 deep-reading 但目录不符合 → 回退 global | |
| 显示 per-paper 模式 | 回退到 zotero_key 检查 | ✓ |

**User's choice:** 显示 per-paper 模式 — 如果有 frontmatter key 就按 per-paper 显示

---

## Deferred Ideas

None — discussion stayed within phase scope
