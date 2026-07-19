# Codebase-Memory-MCP 风险扫描 — 按功能分类 (2026-07-03)

扫描范围：`ocr_*.py` + `ocr_families.py`，覆盖 ~25K 节点知识图谱。
使用 metrics: cyclomatic complexity, cognitive complexity, alloc_in_loop, linear_scan_in_loop, transitive_loop_depth, param_count, lines。

---

## 版面分析 (ocr_document.py) — 七个函数过界

| 函数 | 圈复杂度 | 认知复杂度 | 行数 | 循环/深度 | 风险等级 |
|------|----------|------------|------|-----------|----------|
| `normalize_document_structure` | **84** | 191 | 581 | 20/2 | 🔶 中 |
| `rescue_roles_with_document_context` | **55** | **247** | 307 | 2/2 | 🔶🔶 高 |
| `_detect_body_spine` | **47** | **181** | 294 | 11/3 | 🔶 中 |
| `_resolve_ambiguous_candidates` | **47** | 150 | 325 | 5/2 | 🔶 中 |
| `infer_zones` | 38 | 74 | 381 | 10/1 | 🔹 低 (已规划) |
| `_detect_non_body_insert_clusters` | 36 | 107 | 161 | 6/2 | 🔹 低 |
| `_run_layout_audit` | 25 | 85 | 152 | 7/4 | 🔹 低 |

**重点**: `rescue_roles_with_document_context` — 认知复杂度 247 是圈复杂度 55 的 **4.5 倍**。典型标志：深层嵌套条件里的反向控制流。该函数还包含基于关键词的前言区域检测 (furniture_signals 表)，这个已经被标记为"能力天花板"。

---

## 图片管线 (ocr_figures.py) — 一个巨型函数

| 函数 | 圈复杂度 | 认知复杂度 | 行数 | 循环 | 分配数 | 风险等级 |
|------|----------|------------|------|------|--------|----------|
| **`build_figure_inventory`** | **193** | **546** | **1663** | **51** | **53** | 🔶🔶🔶 极高 |
| `_build_composite_parent_figure_groups_visual_only` | 28 | 78 | 142 | 9 | 5 | 🔶 中 |
| `_infer_missing_main_figure_numbers` | 28 | 46 | 192 | 6 | 0 | 🔹 低 |
| `_build_dense_composite_parent_candidates` | 18 | 41 | 97 | 9 | 6 | 🔹 低 |

**重点**: `build_figure_inventory` 是冷读中**最大的结构风险**。1663 行，193 圈复杂度，546 认知复杂度，51 个循环，53 次循环内分配。它串联了 5 个连续的回退阶段（preproof legend bundling → previous-page locator bridge → sequential → group-aware fallback → 合成父图）。每个阶段都有自己的条件逻辑和数据变换——**所有阶段组合的正确性几乎没有测试能覆盖**。

---

## 渲染 (ocr_render.py) — 性能热点

| 函数 | 圈复杂度 | 认知复杂度 | 行数 | 循环 | 分配数 | 风险等级 |
|------|----------|------------|------|------|--------|----------|
| **`render_fulltext_markdown`** | **144** | **419** | **655** | **39** | **45** | 🔶🔶 高 |
| `_reorder_tail_run` | 39 | 88 | 195 | 5 | **22** | 🔶 中 |
| `_build_heading_style_profiles` | 21 | 64 | 112 | 7 | 6 | 🔹 低 |

**重点**: `render_fulltext_markdown` — 45 次循环内分配对论文生成的峰值内存和性能有影响。`_reorder_tail_run` 195 行中有 22 次 alloc（多个列表推导式 + append）。

---

## 角色分配 (ocr_roles.py)

| 函数 | 圈复杂度 | 认知复杂度 | 风险等级 |
|------|----------|------------|----------|
| `assign_block_role` | **100** | **198** | 🔶 中 |
| `resolve_final_role` | 22 | 53 | 🔹 低 |

`assign_block_role` 是角色的根入口——其缺陷会逐级传播到版面分析和图片匹配中。

---

## 结构门控 (ocr_structural_gate.py)

| 函数 | 圈复杂度 | 认知复杂度 | 行为数 | 风险等级 |
|------|----------|------------|--------|----------|
| `resolve_verified_role` | 43 | 83 | 248 | 🔶 中 |
| `build_verified_reference_zone_from_artifacts` | 29 | 60 | 102 | 🔹 低 |
| `build_document_abstract_span` | 17 | 32 | 136 | 🔹 低 |

---

## 排版 (OCR Families)

| 函数 | 圈复杂度 | 认知复杂度 | 风险等级 |
|------|----------|------------|----------|
| `discover_body_family_anchor` | 6 | 12 | ✅ 低 |
| `discover_reference_family_anchor` | 6 | 14 | ✅ 低 |

---

## 递归

仅有一个递归函数：`ocr_doctor`（带守卫）✅ 无未保护的递归。

---

## 总结

| 风险等级 | 数量 | 关键对应 |
|----------|------|----------|
| 🔶🔶🔶 极高 | 1 | `build_figure_inventory` — 1663行巨型函数 |
| 🔶🔶 高 | 2 | `render_fulltext_markdown` (45 alloc_in_loop), `rescue_roles_with_document_context` (4.5x 认知/圈复杂度比) |
| 🔶 中 | 6 | 版面分析 4 个 + 角色 1 个 + 门控 1 个 |
| 🔹 低 | 5 | 已规划/正常范围内 |

**非风险项（已验证）**: 三个计划内修复覆盖的漏洞、7% body_anchor 失败率被 fallback 兜底、排版分类保守设计、阅读顺序正确、无递归循环。
**新发现的最大风险**: `build_figure_inventory` 的结构复杂度——不是 Bug 问题而是可维护性/变更安全性问题。如果在其中修东西需要极谨慎。
