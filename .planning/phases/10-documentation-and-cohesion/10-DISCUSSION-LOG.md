---
phase: 10
title: Documentation & Cohesion
discussion_date: 2026-04-24
participants: Overseer, VT-OS/OPENCODE
---

# Phase 10 Discussion Log

## Gray Area 1: Architecture Docs Scope

**Question:** ARCHITECTURE.md should be lightweight (quick reference) or comprehensive (full design doc)?

**Options:**
1. 轻量版 — 快速参考（目录结构 + 关键设计决策链接）
2. 完整版 — 面向维护者（设计 rationale、历史决策、扩展指南）

**Discussion:**
- 用户：系统已经稳定，维护者需要理解设计 rationale
- 用户：应该记录关键决策（为什么 commands/ 包、为什么 sync 合并）
- 用户：ADR 风格适合 — 记录决策而非现状

**Decision:** 完整版 — 面向维护者
- ARCHITECTURE.md 包含两层设计、数据流、目录结构 rationale、commands/ 包模式、ADR 风格设计决策记录
- 目标读者：维护者和贡献者
- 每个关键决策记录：问题、考虑选项、选择、后果

## Gray Area 2: Migration Guide Scope

**Question:** MIGRATION-v1.2.md 应该覆盖哪些范围？

**Options：**
1. 最小范围 — 只覆盖命令名变化
2. 完整范围 — 全量迁移（命令名、包名、导入路径、配置、目录结构）

**Discussion：**
- 用户：v1.1 → v1.2 是 breaking change（包重命名）
- 用户：用户需要知道所有变化
- 用户：应该包含回滚/降级说明

**Decision:** 完整范围 — 全量迁移
- 覆盖 v1.1 → v1.2 所有 breaking changes：
  - 命令名变化（selection-sync → sync，等）
  - 包重命名（paperforge_lite → paperforge）
  - 导入路径变化
  - pip 重新安装说明
  - 配置文件变化（如有）
  - 目录结构变化（如有）
  - 回滚/降级说明
  - FAQ 部分

## Gray Area 3: Command Doc Template

**Question:** 命令文档模板应该是什么样的？需要支持多种 Agent 平台吗？

**Discussion：**
- 用户：目前只有 OpenCode，但未来可能支持 Codex、Claude Code
- 用户：模板应该可扩展
- 用户：需要 Agent ↔ CLI 映射的集中参考

**Decision:** 分层结构 — 研究多平台但只实施 OpenCode
- 结构：
  - `docs/COMMANDS.md` — 主参考（Agent ↔ CLI 映射矩阵）
  - `command/*.md` — 详细 per-command 文档，使用统一模板
- 模板必须支持多平台（OpenCode、Codex、Claude Code）
- Phase 10 实施 OpenCode，记录其他平台的方法
- 参考 get-shit-done 的多平台适配经验

## Gray Area 4: Consistency Audit

**Question:** 一致性审计应该自动化还是手动？

**Options：**
1. 全自动化 — 脚本检查所有约束
2. 全手动 — 人工检查清单
3. 混合方案 — 脚本检查硬性约束 + 人工检查软性约束

**Discussion：**
- 用户：硬性约束（旧命令名、死链、broken references）可以用脚本
- 用户：软性约束（术语一致性、风格一致性、branding）需要人工判断
- 用户：混合方案最实用

**Decision:** 混合方案 — 脚本+清单
- 自动化脚本检查硬性约束：
  - 没有旧命令名（selection-sync、index-refresh、ocr run、/LD-*、/lp-*）
  - 没有死链
  - 没有指向 paperforge_lite 的 broken references
- 人工清单检查软性约束：
  - 术语一致性（PaperForge Lite vs PaperForge）
  - 风格一致性
  - Branding

## Summary

所有 4 个灰色区域已解决：
1. 架构文档：完整版，面向维护者
2. 迁移指南：完整范围，全量迁移
3. 命令模板：分层结构，支持多平台
4. 一致性审计：混合方案，脚本+清单

下一步：创建 PLAN.md 并开始执行。
