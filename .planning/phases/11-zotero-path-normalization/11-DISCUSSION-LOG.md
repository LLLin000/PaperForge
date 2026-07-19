# Phase 11: Zotero Path Normalization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 11-CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-24
**Phase:** 11-zotero-path-normalization
**Mode:** discuss (interactive)
**Areas discussed:** 6

---

## Gray Areas Discussed

### 1. 路径规范化时机

| 选项 | 描述 | 选择 |
|------|------|------|
| A. 统一转换 | 在 `load_export_rows()` 中统一转换 | ✓ |
| B. 按需转换 | 保留原始路径，需要时再转换 | |
| C. 双路径存储 | 同时存储原始和相对路径 | |

**决策：** 在 `load_export_rows()` 阶段统一转换所有路径格式为 Vault 相对路径。
**理由：** 避免后续多处重复转换逻辑，与现有 `storage:` 前缀转换保持一致。

---

### 2. 多附件处理策略

**主 PDF 识别：**

| 选项 | 描述 | 选择 |
|------|------|------|
| title==PDF | title=="PDF" 且 contentType=="application/pdf" | ✓ (混合策略的一部分) |
| 取第一个 | 简单取第一个 PDF 附件 | |
| 按大小 | 按文件大小取最大 | ✓ (混合策略的一部分) |

**决策：** 混合策略
1. 首先匹配 `title == "PDF"`
2. 不完全匹配时，分析文件大小 + 标题结构综合判断
3. 最终 fallback 到第一个 PDF

**补充材料处理：**

| 选项 | 描述 | 选择 |
|------|------|------|
| 忽略 | 当前行为，只处理主 PDF | |
| supplementary 字段 | 存储到 `supplementary` frontmatter | ✓ |
| 单独 record | 为每个附件生成 library-record | |

**决策：** 存储到 `supplementary` frontmatter 字段，但标题确定策略延后。

---

### 3. BBT 配置建议

| 选项 | 描述 | 选择 |
|------|------|------|
| 代码适配所有格式 | 不依赖用户配置 | ✓ |
| 代码适配+文档推荐 | 处理所有格式但推荐配置 | |
| 强制要求配置 | 强制用户配置 BBT 输出格式 | |

**决策：** 代码适配所有格式，不依赖用户配置。
**理由：** 符合 PaperForge Lite "降低配置负担" 的设计哲学。

---

### 4. Junction 处理

| 选项 | 描述 | 选择 |
|------|------|------|
| absolutize 中 resolve | 计算绝对路径时 resolve junction | ✓ |
| wikilink 中 resolve | 只在生成 wikilink 时 resolve | |
| 保持现状 | 不处理 junction | |

**决策：** 在 `absolutize_vault_path()` 中 resolve junction。
**理由：** 与现有 `pdf_resolver` 模式一致，计算相对路径前确保路径真实。

---

### 5. 错误处理策略

| 选项 | 描述 | 选择 |
|------|------|------|
| 细化错误状态 | 添加 `path_error` frontmatter 字段 | ✓ |
| 保持现状 | 简单的 `has_pdf: false` | |
| 详细日志 | 只记录日志，不改变 frontmatter | |

**决策：** 添加 `path_error` frontmatter 字段（not_found / invalid / permission_denied）。
**理由：** 用户可直接从 library-record 看到问题，`repair` 可检测修复。

---

### 6. Zotero 目录链接策略

**监工提出的问题：** "如果 Zotero 库不在 Obsidian 里面的话，wikilink 就没有用了。Windows junction 能实现 wikilink 的双向链接生效吗？"

**分析：**
- Obsidian 可以跟随 junction 读取文件
- 但前提是需要先创建 junction
- 如果用户没有 junction，wikilink 失效

**决策：**
- 如果 Zotero 在 Vault 内 → 直接用相对路径，无需 junction
- 如果 Zotero 在 Vault 外 → `paperforge doctor` 检测并建议创建 junction
- 智能检测，不强制单一方案

---

## Deferred Ideas

1. **补充材料标题确定策略** — 多附件时如何识别 "Supplementary"、"Appendix" 等标题
2. **用户后期修改路径配置** — 允许用户更改 Zotero 位置、base/literature 文件夹名称等早期设置
3. **Repair scan 性能优化** — O(n*m) → O(n)，Phase 12
4. **Pipeline 模块清理** — `pipeline/` → `paperforge/`，Phase 12

---

## Corrections Made

None — all assumptions confirmed without correction.

---

*Discussion completed: 2026-04-24*
