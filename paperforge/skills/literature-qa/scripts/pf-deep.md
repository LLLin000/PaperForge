---
name: pf-deep
description: "PaperForge 完整精读 — Keshav 三阶段深度阅读"
argument-hint: "<zotero_key>"
allowed-tools:
  - Read
  - Bash
  - Edit
---

# /pf-deep

## Purpose

基于单篇论文的组会式精读入口。

1. 解析 `/pf-deep <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero 并锁定单篇论文
4. 绑定该论文对应的：
   - <system_dir>/PaperForge/ocr/<KEY>/fulltext.md
   - <system_dir>/PaperForge/ocr/<KEY>/meta.json
   - <resources_dir>/<literature_dir>/.../KEY - Title.md
5. 在正式文献卡片中检查或创建 `## 精读`
6. 以"研究思路 + figure-by-figure"方式一次性完成精读写回

## CLI Equivalent

paperforge sync      # 生成 library-records 和正式笔记
paperforge ocr       # 完成 OCR 提取
paperforge deep-reading  # 查看精读队列状态

> `/pf-deep` 是 Agent 层命令，无直接 CLI 等效命令。其依赖的数据由上述 CLI 命令准备。

## Prerequisites

- library-record 已创建（paperforge sync 生成）
- analyze: true 已设置（在 library-record frontmatter 中）
- OCR 已完成（ocr_status: done）
- fulltext.md 存在且非空
- 正式笔记文件存在

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| <query> | 是（queue 模式除外） | Zotero key、标题片段、DOI、PMID 或关键词 |
| queue | 否 | 启动批量精读队列模式 |

## Example

/pf-deep XGT9Z257
/pf-deep queue

当不提供具体 key/标题时，agent 自动执行以下流程：

1. 运行 paperforge deep-reading 查看精读队列
2. 解析输出的队列状态（analyze=true + deep_reading_status != done + ocr_status）
3. 按 OCR 状态分组展示
4. 由用户选择篇目后批量处理

## Output

Agent 在正式笔记中创建或更新 ## 精读 区域，包含：

- Pass 1: 概览 — 一句话总览、5 Cs 快速评估、Figure 导读
- Pass 2: 精读还原 — Figure-by-Figure 解析、Table-by-Table 解析、关键方法补课、主要发现与新意
- Pass 3: 深度理解 — 假设挑战与隐藏缺陷、结论扎实性评估、Discussion 解读、个人启发、遗留问题

## Platform Notes

### Claude Code
- /pf-deep 在对话窗口直接输入
- Agent 使用 paperforge paths --json 获取 Vault 路径配置
- 多篇文章并行时使用 Task tool 启动 subagent

### Codex
- $pf-deep 在对话窗口直接输入（美元符号前缀）
- 其他行为与 Claude Code 一致

## See Also
- pf-paper — 快速摘要与问答
- pf-sync — 同步 Zotero