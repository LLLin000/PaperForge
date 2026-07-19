# OCR Vision Audit Master — CODE vs VISION 严格分离

> **原则：** 每个检查标注来源。
> `[CODE]` = 从 JSON 文件或 PDF 元数据精确提取，无需视觉判断。
> `[VISION]` = 必须看 `page_NNN.png`，代码没有所需数据。
>
> 字体属性（family、size、weight、color、italic）在 `blocks.structured.jsonl` 的
> `span_metadata` / `span_signature` 中，代码可直接提取。不要用 vision 做字体检查。

---

## 0. 数据源权限

| 文件 | `[CODE]` 可读 | `[VISION]` 需要 |
|------|-------------|----------------|
| `page_NNN.png` | ❌ | ✅ |
| `page_NNN_index.json` | ✅ role, zone, bbox, text | — |
| `block_coverage_summary.json` | ✅ role, raw_label, zone, bbox | — |
| `blocks.structured.jsonl` (OCR 源) | ✅ **span_metadata (font/color/size), span_signature, style_family** | — |
| `block_review.jsonl` | ✅ truth_role, truth_zone, truth_reference_membership | — |
| `figure_table_ownership_summary.json` | ✅ matched/ambiguous/unmatched 计数 | ⚠️ 验证匹配正确性 |
| `fulltext_block_mapping_summary.json` | ✅ found_in_fulltext（排除 noise 后） | — |
| `reference_span_audit.json` | ✅ inside/outside | ⚠️ 边界验证 |
| `coverage_check.json` | ✅ 100% 可靠 | — |

---

## 1. `[CODE]` 自动化可信任检查

以下从 JSON 数据直接提取，**不看图片**，结果决定性的。

### 1.1 Role 一致性 — block_review.jsonl + diff_audit.py

```yaml
输入: block_review.jsonl 的 truth_role vs _current_role
     changed_blocks_after_fallback.json
方法: 字符串直接比较
信任度: 100%
输出: 每个 role mismatch 的 {block_id, pipeline_role, truth_role}
```

### 1.2 Zone 一致性 — block_review.jsonl

```yaml
输入: block_review.jsonl 的 truth_zone vs _current_zone
方法: 字符串直接比较
信任度: 100%
```

### 1.3 渲染完整性 — fulltext_block_mapping_summary.json

```yaml
输入: fulltext_block_mapping_summary.json
      found_in_fulltext=false 且 role ∉ {noise, figure_inner_text, frontmatter_noise}
方法: 前80字符子在渲染全文中的存在性检查
信任度: 高（排除 noise 后），注意子串匹配微小误报可能
输出: 真正在 fulltext 中丢失的 body_paragraph / reference_item / backmatter_body 等
```

### 1.4 图/表未匹配资产 — figure_table_ownership_summary.json

```yaml
输入: figures.unmatched_asset_count, tables.unmatched_asset_count
方法: 直接计数
信任度: 100%
输出: 有未匹配资产的 paper，未匹配数量
注意: 不判断为什么。vision 看具体原因。
```

### 1.5 覆盖完整性 — coverage_check.json

```yaml
输入: coverage_check.json 的 status, missing_block_ids
信任度: 100%
```

### 1.6 字体一致性 — blocks.structured.jsonl

从每个 block 的 `span_signature` 和 `span_metadata` 提取：

```yaml
输入: blocks.structured.jsonl 中所有 text block 的 span_signature
     (font_family_norm, font_size_bucket, bold, italic)
方法: 按 role 分组，检查组内一致性
信任度: PDF 直接提取，100% 精确
```

**具体检查项：**

```
A. 同一 role 内 font_family_norm 一致吗？
   - body_paragraph 应该全是同一字体（如 MyriadPro-Light）
   - 如果某个 body_paragraph 的 font_family 与其他不同 → 混用字体

B. 同一 role 内 font_size_bucket 一致吗？
   - 所有 body_paragraph 的 font_size_bucket 应相同
   - 差异 > 1pt → 字号不一致

C. 标题层次递减正确吗？
   - 按 page 分组，比较 section_heading / subsection_heading 的 font_size
   - H1 > H2 > H3 在字体大小上应有明显递减

D. 同一 block 内混用字体吗？
   - span_metadata 有多个 entries 且 font 不同 → 可能是加粗/斜体标记混入
   - 检查是否合理（如关键词加粗）还是问题（同一字体错误嵌入）

E. 加粗/斜体使用一致吗？
   - 所有 section_heading 的 bold=true？
   - 所有 body_paragraph 的 bold=false？
```

### 1.7 排版布局 — blocks.structured.jsonl + bbox

从每个 block 的 `bbox` 坐标提取：

```yaml
输入: blocks.structured.jsonl 的 bbox [x0, y0, x1, y1]
     page_width, page_height
```

**具体检查项：**

```
A. 对齐方式检测：
   每页取 body_paragraph 的 x0, x1 坐标：
   - 如果所有 x0 相同 → 左对齐 (ragged right)
   - 如果所有 x1 相同且 x0 不同 → 右对齐
   - 如果 x0 和 x1 都跨block一致 → 居中对齐?
   - 如果 x0 都相同但 x1 不同（各行不同长度）+ x1 抵边 → 两端对齐(justified)
   - 跨页一致吗？

B. 列检测：
   每页对 body_paragraph 的 x-center 做聚类：
   - 1个聚类 → 单栏
   - 2个聚类 → 双栏（和 expected 一致？）
   - 聚类中心 x-center 分布均匀？

C. 页边距一致性：
   每页 body_paragraph 的 min(x0) 应大致相同（左页边距）
   每页 body_paragraph 的 max(x1) 应大致相同（右页边距）
   跨页比较左/右边距是否一致

D. 行间距检测：
   同一列相邻 body_paragraph 的 y0 差值减去前一个 block 的高度
   = 段间距
   跨 block 段间距一致吗？

E. 孤行/孤段检测：
   如果一页上某个 body_paragraph 的 height < 正常行高的1.5倍
   且它在页面顶部或底部 → orphan 或 widow
```

### 1.8 引用区间完整性 — reference_span_audit.json

```yaml
输入: reference_span_audit.json 的 status, inside_block_ids
方法: status == "HOLD" → 区间未通过验证
      inside_block_ids 中 role ≠ reference_item/heading → 可能 intrusion
信任度: 状态可靠，intrusion 需要 vision 确认
```

---

## 2. `[VISION]` 必须看图片

以下检查代码**没有所需元数据**，必须看 `page_NNN.png`。

### 2.1 图/表视觉验证

```
- 子面板覆盖：一个 figure 的 asset 列表覆盖了所有视觉上的子面板吗？
- 子面板合并：2x2 的 grid 被合并为 1 个 figure 还是 4 个独立的？
- caption 位置：在图上方/下方？跨页？
- caption 语义：文字描述的内容与图上数据一致吗？（代码读不了图内容）
- 表布局：HTML 表渲染正确？图片表完整无裁剪？
- 角色误标：media_asset 实际上是 table？figure_caption 实际上是 section_heading？
```

### 2.2 图像质量

```
- 分辨率：模糊/锯齿/像素化？
- 仪器截屏：显微镜软件、流式细胞仪输出？
- 对比度：前景/背景区分足够？
```

### 2.3 颜色可达性（仅限图片中的颜色）

```
- 图片本身的配色（热图、荧光图等）
- 是否只依赖红/绿区分条件？
- 注意：文本颜色在 span_metadata.color 中，用代码检查
```

### 2.4 统计完整性（图中数据 vs caption 描述）

```
- 图中显示的误差棒/显著性标记与 caption 描述一致？
- N 值标注了吗？
- p 值标注与图例对应？
- 热图 colorbar 标注完整？
```

### 2.5 Chart 类型识别 + 深度分析

```
识别 chart 类型 → 路由到 paperforge/skills/paperforge/atoms/chart-reading/{TYPE}.md
然后用对应指南做深度检查。
```

### 2.6 引用区间边界验证

```
- 参考页第一页：body 在 "References" 前结束了吗？
- 过渡页：body 和 ref 没有交错？
- reference_zone 外的 reference_item 是否真的是引用条目？
- intrusion candidate 是真的还是 span 边界误标？
```

---

## 3. 不可信自动化结果（不用）

以下数据不作为 finding，只做导航：

| 数据 | 问题 | 替代用法 |
|------|------|---------|
| `same_page_boundary_error` (audit_report.json) | 纯页面角色计数，正常布局也被标 | vision 优先审这些页 |
| `object_ownership_error` (audit_report.json) | 只报 ambiguous/unresolved，漏了大批量 unmatched_assets | 改为读 unmatched_asset_count |
| noise block 的 render_mapping_error | noise 不该在 fulltext 中 | 排除 noise 后看 |
| vision 做字体/颜色检查 | 不准，PDF 元数据更精确 | 用 blocks.structured.jsonl |

---

## 4. 输出格式

```jsonl
{
  "block_id": "p3:12",
  "page": 3,
  "review_status": "reviewed",
  "truth_role": "figure_asset",
  "truth_zone": "display_zone",
  "truth_reference_membership": "outside",
  "evidence": {"annotated_page": "annotated_pages/page_003.png", "method": "visual+bbox"},
  "short_reason": "Fig. 2A MRI image — role and zone correct",
  "vision_checks": {
    "subpanels_merged": "A (2 of 2 panels matched)",
    "image_quality": "OK",
    "chart_type": null
  }
}
```

`vision_checks` 可选，只记录 vision 实际检查的维度，未检查的用 `null`。

---

## 5. 工作流程

```
1. 跑 [CODE]
   diff_audit.py → role/zone mismatch 列表
   fulltext_block_mapping → 真实渲染丢失（排除 noise）
   figure_table_ownership → unmatched_asset_count
   coverage_check → 缺失 block
   blocks.structured.jsonl → 字体一致性、排版异常

2. 决定 vision 目标
   优先:
     - code 发现的 role mismatch block
     - unmatched_asset > 0 的 figure
     - body/reference 在 fulltext 丢失的 block
     - 参考页第一页
     - figure-heavy 页
     - coverage FAIL 的 page

3. 逐 block vision [VISION]
   对选中 block:
     看 annotated page → 确认角色/区域
     如果是 figure → 子面板、质量、chart 路由

4. 输出
   block_review.jsonl 只写 vision 确认过的 block
   不编造未看内容
```
