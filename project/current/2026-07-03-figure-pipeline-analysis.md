# OCR 图片管线全面分析 (2026-07-03)

分析途径：codebase-memory-mcp 图谱查询 + 代码阅读。
核心文件：`paperforge/worker/ocr_figures.py` (6132 行)。
管线入口：`build_figure_inventory(structured_blocks, page_width=1200)` → 返回完整的 `FigureInventory`。
55 个直接被调用者，1663 行纯逻辑，51 个循环结构，10 个处理阶段。

---

## 一、架构总览

```
                         build_figure_inventory
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Phase 0 │ │ Phase 1 │ │ Stage 1 │
              │ 预计算   │ │ 候选组   │ │ 跨页结算  │
              └────┬────┘ └────┬────┘ └────┬────┘
                   │           │           │
                   ▼           ▼           ▼
              ┌─────────────────────────────────┐
              │     Sidecar 侧车厢回退            │
              │     窄列同列题注 → 分区覆盖         │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Preproof Legend Bundle        │
              │   3+ 图例无资产 → 1:1 打包       │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Locator Bridge                │
              │   "前页可见" 图例桥接             │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Group-aware Sequential        │
              │   未匹配组感知顺序回退            │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Classic Sequential Fallback   │
              │   按阅读顺序配对                  │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Unresolved Clusters +         │
              │   Composite Parent              │
              │   未解析簇 + 合成父图            │
              └──────────────┬──────────────────┘
                             ▼
              ┌─────────────────────────────────┐
              │   Final Stage                   │
              │   ID 冲突 / 缺失编号 / 完整性     │
              └─────────────────────────────────┘
```

---

## 二、55 个直接被调用者按功能分组

### 图例检测 (Legend Detection) — 11 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_is_formal_legend` | 13 | 正式图例识别(前缀+编号+分数阈值) |
| `_is_validation_first_legend_candidate` | 13 | "验证优先"图例候选(DWQQK2YB 风格) |
| `_has_strong_explicit_caption_text` | 7 | 强明确题注文本检测 |
| `_has_anchor_supported_legend_context` | 5 | 锚点支持的图例上下文 |
| `_is_insufficient_legend_evidence` | 5 | 证据不足的回绝 |
| `_looks_like_figure_narrative_prose` | 13 | 排除叙述性散文(非真正图例) |
| `_looks_like_inline_figure_mention` | 9 | 排除行内引用("as shown in Fig. 1") |
| `_extract_figure_number` | 8 | 抽取图号(如 "Fig. 1" → 1) |
| `_extract_figure_namespace` | 3 | 抽取图命名空间(figure/supplementary) |
| `_normalized_caption_body` | 6 | 规范化图例文本用于去重 |
| `_validate_page_local_caption_grammar` | 9 | 页级图例句法验证(hypothesis 管理) |

### 计分 (Scoring) — 2 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `score_figure_caption` (ocr_scores.py) | 78 | 图例评分(8 项体征: 编号清晰度/上下文/风格等) |
| `_caption_style_match` | 8 | 图例风格匹配检查 |

### 几何/聚类 (Geometry & Clustering) — 6 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_media_clusters` | 6 | 媒体块空间聚类(gap 阈值) |
| `_build_candidate_figure_groups_from_assets` | 4 | 从资产构建候选组(语义聚类+聚类) |
| `_build_semantic_figure_groups_from_assets` | 4 | 语义感知聚类 |
| `_cluster_bbox` | 2 | 计算一组 bbox 的合并矩形 |
| `_estimate_page_height` | 2 | 从 blocks 估算页面高度 |
| `_partition_assets_by_caption_bands` | 11 | 按题注带切分资产 |

### 配对/计分 (Pairing & Scoring) — 5 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_score_legend_to_group` | 13 | 图例→候选组评分(含多资产一致性加值) |
| `_score_legend_to_asset_with_orientation` | 13 | 单资产评分(含几何方向感知) |
| `_make_local_pairing_hypothesis` | 7 | 构建局部配对假设 |
| `_infer_local_pairing_mode` | 5 | 推断配对模式(same_page/cross_page) |
| `_mark_hypothesis_conflict` | 3 | 标记假设冲突 |

### 匹配/扩展 (Matching & Expansion) — 5 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_expand_matched_assets_locally` | 8 | 本地扩展已匹配资产(吸收相邻块) |
| `_promote_sequence_matches` | 8 | 序列匹配提升(严格分层) |
| `_allow_previous_page_sequential_match` | 5 | 前页匹配门控 |
| `_same_page_narrow_caption_column` | 9 | 侧车厢窄列检测 |
| `_identify_bundle_source_legend_ids` | 7 | 打包源标识 |

### 所有权管理 (Ownership) — 3 个类方法 + 2 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `FigureOwnershipRegistry.__init__` | 5 | 注册表构造(持 used_group_ids/used_asset_page_ids) |
| `FigureOwnershipRegistry.match_group` | 4 | 组匹配标记 |
| `FigureOwnershipRegistry.mark_assets_owned` | 2 | 资产标记为已拥有 |
| `FigureOwnershipRegistry.can_consume_assets` | 4 | 资产消耗可行性检查 |
| `_has_protected_figure_ownership` | 4 | 受保护所有权检查 |
| `_fallback_eligible_asset_page_ids` | 5 | 回退合格资产页 ID |

### 账本/结算 (Ledger & Settlement) — 6 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_build_page_ledger` | 6 | 页级账本(图例数 vs 组数 delta) |
| `_build_residual_ledger` | 8 | 剩余账本(强图例 vs 可匹配组) |
| `_recompute_final_unmatched_assets` | 5 | 重新计算最终未匹配资产 |
| `_reserve_cross_page_objects` | 8 | 跨页预留对象 |
| `_settle_cross_page_reserved_objects` | 10 | 跨页预留结算 |
| `_resolve_figure_id_collisions` | 7 | 图 ID 冲突解决 |

### 合成父图 (Composite Parent) — 4 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_build_composite_parent_figure_groups_visual_only` | 28 | 视觉仅合成父图组构建 |
| `_build_dense_composite_parent_candidates` | 18 | 稠密合成父图候选构建 |
| `_should_suppress_panel_title_candidate` | 10 | 面板标题候选抑制 |
| `_is_safe_page_assets_group` | 16 | 页资产组安全性门控 |

### 资产工具 (Asset Utilities) — 5 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_filter_figure_assets` | 2 | 筛选图资产 |
| `_project_asset_record` | 2 | 投影资产记录 |
| `_asset_page_id` | 2 | 资产页 ID | 标识 ID |
| `_grouped_asset_page_ids` | 4 | 分组资产页 ID |
| `_asset_vertical_side` | 4 | 资产垂直侧判定 |

### 缺失编号恢复 (Missing Number Recovery) — 3 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `_infer_missing_main_figure_numbers` | 28 | 推理缺失主图编号 |
| `_recover_missing_figure_numbers_from_assets` | 18 | 从 PDF 行恢复缺失图号 |
| `_apply_bbox_only_synthetic_vector_fallback` | 6 | 仅 bbox 合成矢量图回退 |

### 完整性 (Completeness) — 1 个函数

| 函数 | 圈复杂度 | 做的事 |
|------|----------|--------|
| `compute_figure_legend_completeness` | 27 | 图例完整性审计(匹配/持有/拒绝/未匹配/含混 五类) |

---

## 三、Phase 0 — 预计算与 Block 分类

**输入**: `structured_blocks` (全部带有 role/zone/bbox 的 block)

**输出**:
- `legends` — 正式图例(已通过 `_is_formal_legend`)
- `rejected_legends` — 不通过正式图例检测但有候选时序
- `assets` — figure_asset + media_asset(过滤 panel label、non_body_insert)
- `figure_locators` — "前页可见图例"标记
- `held_figures` — 验证优先暂缓的图例

**分类逻辑** (行 3021-3111):
1. 跳过 `_non_body_media` 和 `non_body_insert`
2. 跳过单字母面板标签 (`[A-Z]`, `(A)`, `A.`)
3. 对 `body_paragraph` 但 seed_role 是 figure_caption_candidate 的 → 原路线判定为散文, 直接丢到 `rejected_legends`
4. `figure_caption`/`figure_caption_candidate`/`validation_first_candidate`:
   - 运行 PDF 题注前缀恢复(`_recover_figure_heading_prefix`)
   - `_is_formal_legend` 检测 → 通过则 `legends`, 否则 `rejected_legends`
   - 特殊检测: `vision_footnote`+旋转文本+图描述开头 → 挽救到 `legends`
   - 特殊检测: `_is_previous_page_legend_locator` → `figure_locators`
5. 资产分配:
   - `figure_asset` → `assets`
   - `media_asset` — 仅 raw_label 为 image/chart/figure_title/figure 或空时加入

### 资产家族提示 (`asset_family_hint`)
- `figure_like` (raw_label=image/chart/figure_title/figure) — 置信度 0.70
- `table_like` (raw_label=table) — 置信度 0.70
- `ambiguous` (其余) — 置信度 0.35

### 图例去重
对编号图例按 `(namespace, number)` 分组去重, 优先保留:
1. 非 bundle-source 页上的
2. 非 caption-list 页上的
3. 分数更高的
4. 相同分数的优先保留首次出现的
不同编号但相同 `number` 不同文本的 → `_same_number_distinct_keys` (后续保持独立)

---

## 四、Phase 1 — 候选组构建与页内匹配

**输入**: `legends`, `assets`, `ordered_legends`, `candidate_groups`

**处理流程**:
1. **Dense composite parent** (行 3265-3286): 在图例循环之前构建稠密父组合
2. **Panel title suppression** (行 3289-3327):
   - 有编号图例的页面上, 短无编号面板标题被抑制
   - `_should_suppress_panel_title_candidate` 检查文本长度 < 70 + 不在显示区
3. **Candidate group gating** (行 3328-3348):
   - `page_assets` 组在竞争图页面被抑制
4. **Page ledger** (行 3349-3350):
   - `_build_page_ledger` 计算每页图例数 - 候选组数的 delta
5. **Scoring** (行 ~3354-3367):
   - `_score_legend_to_group` 对每对 legend↔group 评分
   - 使用多维度评分: 空间接近度、方向、家族支持、区域支持
   - 三种组类型不同评分策略:
     - `distance_cluster`: 基础分 + 多资产一致性加值 0.15
     - `page_assets`: 需通过 `_is_safe_page_assets_group` 门控
     - `single_asset`: 直接使用 `_score_legend_to_asset_with_orientation`

---

## 五、Stage 1 — 跨页预留与结算

**输入**: `matched_figures`, `ordered_legends`, `candidate_groups`, `_page_blocks_by_page`

**处理流程**:
1. **Cross-page reservation** (行 ~3367-3947):
   - `_reserve_cross_page_objects` 在页面间预留双向引用
   - 预留基于图例-组配对的证据强度
   - reserved legends look backward (寻找前页资产)
   - reserved groups look forward (寻找后页图例)
2. **Primary cross-page settlement** (行 3948-3964):
   - `_settle_cross_page_reserved_objects` 执行预留对象的实际结算
3. **Failed groups handling** (行 3973-4002):
   - 多资产组 → `unresolved_clusters`
   - 单资产 → `unmatched_assets`

---

## 六、Sidecar 侧车厢回退

**位置**: 行 ~4004-4222

**适用**: 窄列同列正式题注的页面 (如横排两个独立图, 各有自己的窄列题注)

**机制**:
- 通过 `_same_page_narrow_caption_column` 检测是否为侧车厢页
- 对侧车厢页, 使用 `_partition_assets_by_caption_bands` 按题注带切分资产
- 题注带的资产按垂直区域分配给最近题注
- 非侧车厢页保持常规 gap/overlap 匹配逻辑

**与正常匹配的差异**: 侧车厢的可见图/题注配对是基于列的, 不是基于 gap/overlap 的。
常规空间匹配器无法可靠地将资产分配给窄列侧车厢题注——所以需要这里特殊处理。

---

## 七、预印版图例打包回退 (Preproof Legend Bundling)

**位置**: 行 ~4223-4346

**适用**: 单页有 >=3 个图例且没有任何同页资产 → 按页码顺序 1:1 打包到后续资产页

**机制**:
- 从 bundle-source 图例页收集 >=3 个图例
- 检查通过页面 (无 body/table 中断)
- 按顺序匹配图例 → 后续资产页
- **保护距离聚类的多资产组不被回退消耗**
- 结果: `matched_figures` 中有 `legend_bundle_match` 标记, 置信度 0.3

---

## 八、前页图例定位桥 (Previous-page Locator Bridge)

**位置**: 行 ~4347-4542

**适用**: "Fig. 10 (See legend on previous page.)" 模式

**机制**:
- 定位图例的页面 → 获取前页的同编号完整图例
- 定位页 → 获取定位图例上方的视觉组
- 桥接三个组件: 前页完整图例 + 定位页视觉组 + 定位图例本身
- 结果: 匹配置信度 0.5, flags=previous_page_locator_match
- 替换 ambiguity 条目以避免重复匹配

**保护条件**:
- 仅当定位图例在前页有完整图例(>=60 字符, 非自身定位标记)
- 仅当定位页上方有视觉组
- 仅当页面间无 body/table 中断

---

## 九、组感知顺序回退 (Group-aware Sequential Fallback)

**位置**: 行 ~4543-4672

**适用**: 没有被同页图例认领的未匹配 `distance_cluster`

**机制**:
- 收集未被使用的组 (包括 `distance_cluster` 和 `single_asset`)
- 按页面 + 垂直位置排序
- 对每个未匹配的图例, 在之后的页面上查找最合适的组
- **在旧式单资产回退之前执行**, 确保组优先于裸资产

---

## 十、经典顺序回退 (Sequential Fallback)

**位置**: 行 ~4674-4783

**适用**: 未匹配图例 → 任何剩余资产

**机制**:
- 图例和图形经常出现在不同页——按阅读顺序匹配
- 从候选组过滤后, 对未聚类的资产与未匹配图例配对
- 限制: 不能消耗属于任何候选组的资产
- 支持前页匹配 (`_allow_previous_page_sequential_match`)

**缺陷**: 这是最宽泛的回退——如果前序阶段都没有匹配成功, 它会尝试任何组合。
这是已知的 tradeoff: "Captions and figures often appear on different pages — humans
match them by sequential reading order, not spatial proximity."

---

## 十一、未解析簇 + 合成父图 (Unresolved Clusters + Composite Parent)

**位置**: 行 ~4785-4873

**处理流程**:
1. **未解析簇**: 被回绝图例页面上的未匹配资产 → `_media_clusters` 聚簇
2. **合成父图候选**: `_build_composite_parent_figure_groups_visual_only` + `_build_dense_composite_parent_candidates`
3. **稠密页面整合**: 有合成父图候选的页面上, 剩余未匹配资产被组合到未解析簇
4. **跨页结算后清理**: 已匹配 figure 的 block 从未解析簇中移除

---

## 十二、最终阶段 (Final Stage)

**位置**: 行 ~4874-5114

**处理流程**:
1. 页内图例句法验证 (`_validate_page_local_caption_grammar`)
2. 从未解析簇中移除已匹配 figure 的 block
3. `_resolve_figure_id_collisions` — 处理 ID 冲突
4. `_infer_missing_main_figure_numbers` — 推理缺失的编号
5. `_apply_bbox_only_synthetic_vector_fallback` — bbox-only 合成矢量图回退
6. `_recover_missing_figure_numbers_from_assets` — 从 PDF 行推断资产内部缺失图号
7. `compute_figure_legend_completeness` — 五类图例审计

---

## 十三、关键数据结构

### FigureOwnershipRegistry
核心状态管理类, 追踪:
- `used_group_ids: set[str]` — 已被匹配的组 ID
- `used_asset_page_ids: set[tuple[int, str]]` — 已被占有的资产 (page, block_id)
- 方法: `match_group`, `mark_assets_owned`, `can_consume_assets`

**设计**: 可变集合, 在 1663 行函数中就地更新。没有事务/回滚机制。
这意味着某个阶段的错误匹配会污染所有后续阶段的可用性计算。

### matched_figures
管线的主产物。每个条目:
- `figure_id`, `figure_namespace`, `figure_number`
- `legend_block_id`, `text`
- `matched_assets: list[dict]`, `asset_block_ids`
- `page`, `legend_page`, `asset_pages`
- `match_score: {score, decision, evidence}`
- `confidence: float`
- `flags: list[str]`
- `settlement_type: str` (same_page / cross_page / legend_bundle / previous_page_legend_locator / sequential)
- `caption_score: dict`
- `bridge_block_ids: list[str]` (只在 locator bridge 时非空)

---

## 十四、处理流程全景

```
structured_blocks
 │
 ▼
[Phase 0: Block Classification]
 │  legends, rejected_legends, assets, figure_locators, held_figures
 │  asset_family_hint annotation
 │  legend dedup by number+namespace
 ▼
[Phase 1: Candidate Groups + Page-internal Matching]
 │  candidate_groups (distance_cluster / page_assets / single_asset)
 │  _score_legend_to_group → matched_figures (same_page)
 ▼
[Stage 1: Cross-page Reservation + Settlement]
 │  _reserve_cross_page_objects → reserved_legend_ids / reserved_group_ids
 │  _settle_cross_page_reserved_objects → matched_figures (cross_page)
 ▼
[Sidecar Fallback]
 │  narrow same-column captions → caption-band partition
 │  override normal matching when detected
 ▼
[Preproof Legend Bundling]
 │  3+ legends, 0 same-page assets → 1:1 bundle to subsequent asset pages
 ▼
[Previous-page Locator Bridge]
 │  "See legend on previous page" → connect full legend + visual group
 ▼
[Group-aware Sequential Fallback]
 │  unmatched distance_clusters → unmatched legends (in page order)
 ▼
[Classic Sequential Fallback]
 │  unmatched legends → any remaining assets (reading order)
 ▼
[Unresolved Clusters + Composite Parent]
 │  spatial clusters of unmatched assets on rejected-legend pages
 │  composite parent + dense parent constructions
 ▼
[Final Stage]
 │  ID collision resolution
 │  Missing number inference
 │  Completeness audit
 ▼
FigureInventory
```

---

## 十五、风险总结

### 高风险

1. **`build_figure_inventory` 巨型函数 (1663 行)**
   - 10 个顺序阶段, 每个阶段有自己的条件逻辑
   - 没有事务/回滚: 所有权注册表是可变集合
   - 一个阶段的错误匹配污染所有后续阶段
   - 5 个回退阶段之间有复杂的优先级和互斥条件

2. **5 个串行回退阶段的组合覆盖**
   - 每个回退阶段对前一阶段的输出进行操作
   - 没有测试覆盖所有阶段组合
   - 某些论文可能触发多个回退阶段, 它们的交互未明确测试

3. **Performance: allocate_in_loop=53**
   - 在 51 个循环中有 53 次分配
   - 对大型论文(50+ 图), 每次重建都会触发大量内存分配
   - `render_fulltext_markdown` 也有 45 次循环内分配

### 中风险

4. **组反转/图例去重依赖顺序**
   - 去重仅基于编号+命名空间, 不包含页面位置上下文
   - 若两块编号相同的图例在不同页, 系统可能只保留一个

5. **sidecar 检测是硬编码的**
   - `_same_page_narrow_caption_column` 依赖固定的列宽阈值
   - 对某些自由格式期刊可能误判

6. **Bundle 回退的门控条件复杂**
   - 跨越多个页面的 body/table 中断检测
   - `_NON_PURE_ROLES` 集硬编码了 8 个角色

### 低风险 (设计选择)

7. 顺序回退是宽泛的但已知 tradeoff (代码注释已承认)
8. 合成父图构造使用视觉聚类而非语义信号
9. 置信度阈值 (0.3/0.5/0.72/0.85) 是硬编码的, 没有从数据中学习

### 已覆盖 (不在此模块)

- 版面分析的前言区域泄漏已在三个计划修复中涵盖
- 列感知题注前缀恢复已实现
