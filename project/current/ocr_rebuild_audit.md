# OCR Rebuild 全量审计报告

> 审计范围: 452 篇 rebuild 论文 | 2026-06-19
> 状态: post-readiness audit surface
> 角色: evidence source for rebuild hardening
> 不改变: 已完成的 OCR-v2 readiness-gate 结论

本审计在 readiness-gate 完成后评估了全量语料的 rebuild 输出质量。
它定义的是 post-readiness hardening 工作；不重新打开 OCR-v2 骨架决策。

---

## 1. HEALTH 总览

| 颜色   | 数量 | 比例 |
| ------ | ---- | ---- |
| GREEN  | 21   | 5%   |
| YELLOW | 276  | 61%  |
| RED    | 155  | 34%  |

### 1.1 Issue 前向模拟

若修复所有已识别问题后的预期分布:

```
            修前    修后
GREEN:       5%  →  28%
YELLOW:     61%  →  62%
RED:        34%  →  11%
```

剩余 48 篇红色主要是真实的图表匹配失败，不是阈值可救的。

### 1.2 健康判定逻辑

`ocr_health.py:172-193` — 7 个二元门:

```python
if caption_without_media > 0:   issues += 1  # 360 篇
if media_without_caption > 0:   issues += 1  # 371 篇
if empty_tables > 0:            issues += 1  # 113 篇
if not abstract_found:          issues += 1  # 15 篇
if not references_found:        issues += 1  # 6 篇
if section_heading_count < 2:   issues += 1  # 42 篇
if formal_legend_gaps > 0:      issues += 1  # 69 篇
```

`> 0` 阈值对大小论文同等惩罚，无 ratio 或加权。

---

## 2. 数据总揽

### 2.1 Figure 匹配

```
总 Caption: 2488  |  Matched Assets: 1893  |  匹配率: 76%
Caption w/o media: 1107 (avg 2.4/篇, 360 篇)
Media w/o caption: 2306 (avg 5.1/篇, 371 篇)
P50: 0.75  |  P10: 0.33  |  0 匹配: 13 篇
```

### 2.2 Table 匹配

```
总 Caption: 727  |  Matched Assets: 513  |  匹配率: 71%
Tables w/o asset: 214 (29%)
P50: 1.00  |  P10: 0.00  |  0 匹配: 35 篇
```

### 2.3 Block 角色分布 (50 篇采样)

```
reference_item:    28.9%    noise:             19.9%
body_paragraph:    19.6%    unknown_structural:  5.0%
subsection_heading: 3.9%    figure_asset:        3.6%
media_asset:        3.4%    figure_inner_text:   2.5%
figure_caption:     2.1%    section_heading:     1.7%
footnote:           1.4%    table_caption:       0.6%
abstract_body:      0.5%
```

### 2.4 Subject 名称问题

`ocr_health.py:130`:
```python
figure_asset_count = len(figure_inventory.get("matched_figures", []))
```
这是 **matched figure 数量**，不是 asset 数量。命名误导维护判断。

---

## 3. 已确认的 BUG（代码级验证）

### 3.1 Heading 计数只数 `section_heading` — CRITICAL

`ocr_health.py:118`:
```python
section_heading_count = sum(1 for b in structured_blocks if b.get("role") == "section_heading")
```

不含 `subsection_heading`、`sub_subsection_heading`。

实测:
```
23T2B8ZX: health=1, actual=9  (1 sec + 8 sub)
27MSS3VH: health=0, actual=8  (0 sec + 7 sub + 1 subsub)
```

**修复方向**: 三类 heading 总数。

### 3.2 Footnote 渲染为 body text — CRITICAL

`ocr_render.py:1226-1237` — `_SKIPPED_BODY_ROLES` 不含 `"footnote"`。

所有 footnote 掉入 `else` 分支当纯文本 body paragraph 渲染。验证 (23T2B8ZX p=1): 3 块 footnote (`raw_label=footnote`) 分类正确，但全文当正文输出。

**修复方向**: footnote 从正文跳过；但 table note 要提前被 table inventory 消费。

### 3.3 Table caption 被渲染成 blockquote

`ocr_render.py:1359-1374` — `table_caption` 分支输出:

```md
> **Table X ...**
![[render/tables/table_XXX.md]]
```

导致 caption 重复、table note 漂浮。**修复方向**: fulltext 主流只输出 table embed；caption + note + crop 放进 `render/tables/table_XXX.md`。

### 3.4 `Table N` 短 caption 被 held / unmatched

`ocr_tables.py:16-18` — `_TRUNCATED_TABLE_ONLY_PATTERN` 匹配 `"Table 1"` → `_is_weak_explicit_table_caption` → True → held。

69TA9S8W 类型（12 个 table 全是 `"Table N"`）全部 unmatched。**修复方向**: 强几何证据 + `raw_label=table` 时允许匹配。

### 3.5 `note_block_ids` 是 dead field

`ocr_tables.py:251` 写入 `note_block_ids`，但 `ocr_objects.py` 和 `ocr_render.py` 都不消费。就算识别到 table note 也不会进 table card，不会从正文移除。

---

## 4. 结构性问题（需设计级修复）

### 4.1 Supplementary figure namespace 碰撞

`_extract_figure_number("Figure S1")` 返回 `1`，`"Figure 1"` 也返回 `1`。在同一个整数 namespace 竞争。

当前 dedup "保留第一个" 能防止 S figure 偷正文 figure，但 Supplementary Figure 可能被直接丢掉。正确修法是 figure key 改为 tuple:

```python
("main", 1) / ("supplementary", 1) / ("extended_data", 1)
```

对应输出: `figure_001` / `figure_s001` / `figure_ed001`

### 4.2 Reference 排序

`ocr_render.py:604-619` — `_sort_blocks_by_column` 对所有 tail block 按 `(col, y, x)` 排序。19% 论文有 ref 错序。

修复应分层:
1. 解析 `[1]` / `1.` 编号，按编号递增
2. 检测 ref 区是否双栏 → 双栏用 `page → col → y`，单栏用 `page → y`
3. 保留 OCR 原始相邻关系作 tie-breaker

### 4.3 Figure/Table 资产所有权冲突

`ocr_tables.py:90` 当前已加了宽高/aspect 过滤，但宽图仍可能同时进入 figure 和 table 候选。需要统一 figure/table asset 仲裁机制，避免重复 orphan。

### 4.4 `page_assets` group 风险

当前（已修改未合并）给同页 ≥3 asset 建 `page_assets` group，固定 score 0.55，按先到先得匹配。风险：可能把同一页多个独立 figure 的 assets 一次性占掉。

应加 gate:
- 同页只有一个 formal legend
- 或无其他 figure/table caption
- 或 reader 层仅为 ASSET_GROUP 参考，不作为 strict match

### 4.5 Figure completeness gap 根因不只是 caption_score

`caption_score < 0.4` → `unmatched_legends` 理论上被 accounted。真正产生 gap 的是:
- dedup 后被静默丢弃的重复编号 caption
- `rejected_legends` 没进 outcome bucket
- body mention / supplementary caption 被过滤后仍被 completeness 统计

每个 numbered caption 必须有明确 outcome: `matched / held / ambiguous / unmatched / rejected / deduped_duplicate / supplementary`

### 4.6 `references_found` 信号太弱

`ocr_health.py:123-125`:
```python
references_found = any(
    b.get("role") in ("reference_heading", "reference_item")
    or b.get("raw_label") == "reference_content"  # ← 一个 label 就过
    for b in structured_blocks
)
```

更合理的是: `reference_zone.status == ACCEPT` 或 `reference_item_count >= 阈值`。

---

## 5. Table Notes 识别

### 5.1 当前状态

- Table caption 分类准确率 100%
- `note_block_ids` written but dead (不被任何 reader 消费)
- 30 篇采样中 32 个 `footnote` block 在 table 页面上，0 个关联到 table
- `render_table_object_markdown()` 只写 caption + 图片，无 note

### 5.2 修复方向

1. `build_table_inventory` 存入 `note_texts`
2. `render_table_object_markdown` 消费 note 并输出
3. 关联逻辑应包含: `footnote` role + `vision_footnote` raw_label + 紧邻下方短 text

---

## 6. 非图表内容审计

### 6.1 `unknown_structural` (1217 块)

```
530 有文本:
  - 185: journal metadata (correctly excluded)
  - 306: genuinely unclassifiable short fragments
  - 27:  real body paragraphs misclassified (content loss, 0.3%)
687 空: images/decorations (correctly ignored)
```

仅 27 块真实丢失，`unknown_structural` 基本工作正常。

### 6.2 其他

- Body paragraph 完整性: OK
- Heading 风格分布: 正常
- Fulltext 大小 vs raw: 无显著内容丢失
- 短 body paragraph (<5 词): 56 个，多为页眉/DOI 碎片

---

## 7. 已完成的代码修改（待验证合并）

| 修改                                                | 位置                        | 状态     |
| --------------------------------------------------- | --------------------------- | -------- |
| Figure 编号 regex 支持 "Figure S.X"                  | `ocr_figures.py:15`           | 已改     |
| Table 编号 regex 支持 "Table S1"                    | `ocr_tables.py:11`            | 已改     |
| Table media_asset 加 raw_label/aspect 过滤           | `ocr_tables.py:90-97`         | 已改     |
| Figure cluster_bbox 用全量 assets 重算              | `ocr_figures.py:1136-1137`     | 已改     |
| Figure dedup: 双方有 asset 时保留第一个             | `ocr_figures.py:862-863`       | 已改     |
| Figure 行列约束放宽 (0.35→0.6, gap 8%→12%)         | `ocr_figures.py:436-447`       | 已改     |
| Figure `page_assets` group type (≥3 per page)       | `ocr_figures.py:424-427`       | **待审** |
| Figure `page_assets` 评分 (0.55 + family bonus)     | `ocr_figures.py:474-488`       | **待审** |

---

## 8. 建议修复优先级

### 第一批: 污染正文 / 静默丢失

| 优先级 | 项目                         | 影响                      |
| ------ | ---------------------------- | ------------------------- |
| P0     | footnote 从正文移除 + table 消费 | 24 篇正文 noise 消失       |
| P0     | table caption 取消 blockquote | 46% 论文格式修正           |
| P0     | heading 计数含三类           | ~30 篇 red→yellow          |
| P0     | Table N 强几何匹配           | 69TA9S8W 类型全匹配        |
| P1     | supplementary namespace 拆分 | S figure 碰撞根治 (46 篇)  |
| P1     | page_assets 加 gate          | 防整页吞图                 |
| P1     | table note 进 object render  | note 归位，不再散落正文   |

### 第二批: 匹配优化 / 评分改善

| 优先级 | 项目                           | 影响                      |
| ------ | ------------------------------ | ------------------------- |
| P2     | reference 编号解析 + col/y 排序  | 19% 错序修复               |
| P2     | figure/table asset 所有权仲裁  | 孤儿减半                   |
| P2     | health 二元→ratio/weighted     | 评分解释性提升             |
| P2     | completeness gap 补齐 7 个桶   | gap 不再误报               |
| P2     | `references_found` 改为 zone 检测 | 不再被 raw_label 欺骗      |
