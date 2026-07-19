# P2 Issues — 具体信息 + 修法

## P2#1a: Legend 跑到 figure 前面（Previous-page locator）

### 现象
合图形（composite figure）的 full legend 在上一页，当前页只有 locator caption（"Fig. X (See legend on previous page.)"）。full legend 没被匹配到当前页的 visual group，渲染出乱。

### 具体论文
- **WV2FF4NV** — Fig.10（三面板合图）
  - page 15: full legend "Fig. 10. [完整 legend 文本]"
  - page 16: locator caption "Fig. 10 (See legend on previous page.)"（block_id=9, y=1385-1407）
  - page 16: 三个 figure_asset 面板（id=3,5,8），构成 visual group

### 根因
管道把所有 `figure_caption` 一视同仁做 same-page 空间匹配。locator caption "Fig. 10 (See legend on previous page.)" 被当成普通 caption，尝试在 page 16 匹配 assets → 它下方没有 assets → 匹配失败 → 进入 generic fallback。上一页的 full legend 在 page 15 孤零零 unresolved。

管道没有识别 "locator caption" 这个概念，也没有桥接机制把 locator + previous full legend + current visual group 串起来。

### 当前代码（相关路径）
- `ocr_figures.py:4094-4212` — legend_bundle fallback（按顺序配对，不是编号）
- `ocr_figures.py:4214-4356` — group-aware sequential fallback
- `ocr_figures.py:4357-4601` — generic sequential fallback（空间距离匹配）
- `ocr_figures.py:2520-2600` — same-page spatial matching（locator 在此失败）

### 正确修法 — Previous-page Legend Locator Bridge

**核心原则**：不是全局规则，而是 single-figure exception handler。正常匹配优先，bridge 后置。

#### 架构

```
1. 收集 legends/assets（正常流程）
2. 识别 locator caption → 从 full legend 候选里拿掉
3. 正常 same-page matching（locator 不参与）
4. 对仍 unresolved 的 previous-page full legend 启动 locator bridge
5. bridge 成功后移除旧 unresolved 记录
6. 后续 generic fallback 不再碰这张图
```

#### Locator 识别条件

```python
locator_text matches:
  Fig/Figure + number + see/refer + legend/caption + previous/preceding page
```

识别后：
- 从 ordinary legends 中移除
- 存入 `figure_locators[]`，只做 bridge evidence
- `continue` — 不进入普通 figure_caption matching

#### Bridge 启动条件（全部必须满足）

```python
full_legend:
  page == locator_page - 1
  same figure_number
  not locator itself
  has strong caption text (>=80 chars, not just locator)
  currently UNMATCHED by normal same-page matching

visual_group:
  page == locator_page
  unowned / unresolved
  bbox is above locator bbox
  multi-asset or composite_parent preferred

anti-overreach:
  no other same-number full legend on locator page
  do NOT bridge if full_legend already has a valid same-page match
```

#### 输出

```python
{
  "figure_id": "figure_010",
  "figure_number": 10,
  "legend_block_id": full_legend_block_id,   # 来自上一页
  "legend_page": previous_page,
  "text": full_legend_text,                   # 完整 caption 文本
  "locator_caption_block_id": locator_block_id,
  "locator_page": current_page,
  "page": current_page,
  "matched_assets": current_page_assets,
  "asset_block_ids": [...],
  "cluster_bbox": visual_group_bbox,
  "settlement_type": "previous_page_legend_locator",
  "flags": ["explicit_previous_page_locator"]
}
```

#### 代码位置

插入 `build_figure_inventory()` 中：
- **在** normal same-page matching（~line 2600）**之后**
- **在** generic sequential fallback（~line 4094）**之前**

#### 注意：不要扩大到 cluster numbering

这个 case **不需要**给所有 cluster 加上 figure_number。当前页已经有 OCR 到的编号文本（"Fig. 10"），缺的是：

```
locator caption → current visual group  （通过编号）
locator caption → previous full legend   （通过编号）
```

不是给 cluster 编号，是识别 locator 然后用编号搭桥。

#### 和 containment 问题分离

P2#1a 只解决 full legend + visual group 的 ownership。图内 panel title 跑乱（"Subchondral evaluation"、"Cartilage evaluation"）是 containment 问题（见 P2#1b），分两个 commit 修。

---

### 当前代码
- `ocr_figures.py:4094-4212` — legend_bundle fallback 匹配
- `ocr_figures.py:4214-4356` — group-aware sequential fallback
- `ocr_figures.py:4357-4601` — old sequential fallback

### 根因
数据模型问题：figure cluster（distance_cluster / unresolved_cluster）没有 `figure_number` 字段。**每个 cluster 只有几何信息**（`cluster_bbox`, `page`, `asset_block_ids`），不知道自己对应的 figure 编号。legend 知道自己的编号（通过 `_extract_figure_number`），但 **没有任何机制能把编号传给 cluster**。

所以在所有 fallback 路径中，legend 和 cluster 的配对只能靠**空间/位置顺序**，不能靠编号：
- legend_bundle（line 4165-4166）：`for idx, cap in enumerate(caps_sorted): ap = valid_pages[idx]` — 按枚举顺序，不是编号
- group-aware（line 4241+）：按 same_page→next_page→prev_page 排序，fn 只用来格式化 fig_id
- sequential（line 4357+）：按 page+bbox 排序配对

当 legend 的空间顺序和编号顺序不一致时（多栏、跨页、合图形），匹配就错了。

### 修法（架构级，3d+）
给 cluster 加上 figure_number 检测。需要：从 figure 图像区域内的文字（"Fig. X"）提取编号并关联到 cluster。管道需要：

1. 在 `_candidate_group_entry`（line 778）或 `_project_asset_record` 中增加 `figure_number` 字段
2. 从图形区域的 OCR 文字（如果有）或 figure 内部标签检测获取编号
3. 所有 fallback 路径改为编号优先、空间距离辅助

### 限制
- 仅对纯图（raster image）有效：不一定能从图像中提取到 "Fig. X" 文字
- 对矢量图/表格需要不同方法
- 现有匹配模式可能已经覆盖了多数情况，真正出错的场景有限

---

## P2#1b: 图内文字漏检（严重）

### 现象
`vision_footnote` raw_label 的块（subfigure 标签、子图注）在合图形内部，但被标为 `footnote` 而不是 `figure_inner_text`。图形结构不完整。

### 具体论文
- **UGA8GFAR 第2页**（Fig.1，31个子图）
  - id=7,9,11,14,27,29,31,33,35,37,39: 11个 `vision_footnote` 块
  - 文字："Single outlet", "Multiple outlets", "Sequential outlets", "Flexible electronic patch", "Microneedle device" 等
  - 全部在 visual container 内，全部被标为 `footnote`
- **JMG23U8Q 第4页**（Fig.3）
  - id=5: text="1"（subfigure 标签），bbox=[448,479,461,581]，在 visual container 内
- **AW49IHEX 第6页**（Fig.3）
  - id=14: text="Scaffold-free techniques"，在 visual container 内

### 当前代码
- `ocr_figures.py:5040-5058` — `tag_figure_contained_text` 遍历 block，检查 `_is_contained`
- `ocr_figures.py:4937-4954` — `_is_contained` 检查 block 中心在 figure region 内 + 85% 面积重叠
- `ocr_figures.py:4977-4988` — `_figure_region_bbox` 使用 `cluster_bbox`
- `ocr_figures.py:3791-3792` — `cluster_bbox` 只从 matched_assets 的 union 计算
- `ocr_figures.py:4889-4894` — `_LEAK_ROLES` 包含 `footnote`（允许 footnote 被提升为 figure_inner_text）
- `ocr_figures.py:5030` — fallback 资产过滤的 raw_label 集合：`{"image","chart","figure_title","figure"}`
- `ocr_roles.py:1325-1329` — `vision_footnote` → `role=footnote`

### 根因
`tag_figure_contained_text` 的 containment 检查只使用 `cluster_bbox`（所有已匹配资产块的 bbox 并集）。但 `vision_footnote` 类文本块（子图标签、面板标题）在合图形的**资产之间的间隙**中，不在 `cluster_bbox` 内。

`_is_contained` 返回 False → 即便 `footnote` 在 `_LEAK_ROLES` 中，也无法被提升为 `figure_inner_text`。

虽然 `_container_bbox`（PyMuPDF 视觉容器检测的完整图形范围）已经存在（`ocr_pdf_spans.py:484-495`），但 `tag_figure_contained_text` **从未引用它**。

### 修法
在 `tag_figure_contained_text` 中，containment 区域构建时应该**优先使用图形合并后的包络区域**（所有 cluster 内块的并集 bbox），而非仅资产块的 `cluster_bbox`。

具体来说，在 `_figure_region_bbox` 中增加一个来源：当 `matched_figures` 中有合图形（多个 asset 或 composite parent）时，用所有 linked block 的包络 bbox 而非仅 asset union。

**注意**：不要引入 `_container_bbox` 到 figure inner-text 检测逻辑——容器检测和图形合并应该保持独立，否则一个出错了会影响另一个。

---

## P2#2: "Table N" 短图注不匹配（影响33篇论文）

### 现象
PDF 提取把表格图注拆成两个相邻文本块。前一块是裸 "Table N"（无正文），后一块是描述性正文。后一块被错误分类为 `figure_caption`，table pipeline 看不到它。

### 具体论文
- **2HJSWV3V 第7页**
  - id=11: "Table 2" → `table_caption`, y=554-572
  - id=12: "Structural parameters of nanocomposites, obtained from the d" → `figure_caption` ← 错，y=571-593
  - id=13: [表格内容] → `media_asset`, y=597-648

另有多篇论文有同样模式（共33个 captions 在结构化数据中不匹配）。

### 当前代码
- `ocr_tables.py:15` — `_CONTINUATION_PATTERN = r"(cont(?:inued)?\.?)"` — 只认显式 (cont) 标记
- `ocr_tables.py:16-19` — `_TRUNCATED_TABLE_ONLY_PATTERN` — 匹配裸 "Table N" 后缀不能有正文
- `ocr_tables.py:51-53` — `_is_insufficient_table_caption_evidence`
- `ocr_tables.py:222-297` — weak explicit caption 匹配路径（gate 太严）
- `ocr_roles.py:758-770` — body_paragraph + legend_like + figure_title → `figure_caption`（第二块被标为 `figure_caption` 的路径）

### 根因
两块属于同一个 caption，但被独立处理：

1. 第一块 "Table 2" → `_TRUNCATED_TABLE_ONLY_PATTERN` 匹配 → `is_weak_truncated=True` → 进入 weak explicit path
2. 第二块 "Structural parameters..." → 不以 "Table" 开头、无 table marker → 角色解析走 `body_paragraph + legend_like + figure_title` → **`figure_caption`**
3. Table pipeline 的 caption 收集（line 148）只收 `table_caption`/`table_caption_candidate` → 看不到第二块
4. 第二块的 `figure_caption` 插在 `table_caption` 和 `media_asset` 之间 → 匹配算法被迷惑

`_is_continuation_caption`（line 32-33）只检测文本中是否包含 "(cont)"，不处理这种 OCR 分裂导致的相邻未标记延续。

### 修法（1-4h，稳健，不用字体/风格启发式）
在 `build_table_inventory` 的 caption 收集后，对每个 `is_weak_truncated` 的 caption（裸 "Table N"）：

1. 扫描同一页上**紧邻的下一个 block**
2. 检查条件：
   - `page` 相同
   - `y_start_new_block - y_end_caption < 阈值`（~20px，同列内）
   - 两个 block 的 bbox 在 x 轴上重叠（同一列，非并排）
3. 如果满足 → 合并 text，更新 bbox end，标记续块为已消耗
4. 用合并后的完整文本重新做匹配

参考已有模式：`_merge_adjacent_headings` 在 `ocr_blocks.py` 中。不需要 font/style 匹配，只靠空间邻接。

**同样影响 figure caption？** 查了，figure pipeline 有 `_is_insufficient_legend_evidence` 但没有 adjacent-merge 逻辑。第二块 "Structural parameters..." 如果没有 figure number，在 figure pipeline 中会成为 unmatched_legend → 直接被丢弃。所以**figure 侧同样受影响**。

---

## P2#4: 页眉进入正文（低影响）

### 现象
Running header "SHOULDER ANATOMY AND ROTATOR CUFF TEAR" 在渲染输出的正文中重复出现（在多个页面上各出现了两次）。

### 具体论文
- **4DU8LEH2**
  - 第4页：id=1（正常OCR）+ id=2（backfill）→ 都包含页眉文字
  - 第10页：同样模式
  - id=2 的 `_text_source=pdf_text_layer_fallback`, `role=body_paragraph`

### 当前代码
- `ocr_roles.py:1280-1295` — `raw_label == "header"` → `noise`（正常工作在第2页）
- `ocr_roles.py:1343-1576` — `raw_label == "text"` path（第4页走这里，无页眉检测）
- `ocr_families.py:240-292` — `_classify_style_family`，无 running header 概念
- `ocr_roles.py:209-260` — `_looks_like_margin_band_noise`，只检测极窄/极高边带，不匹配短宽居中文本

### 根因
PaddleOCR 在第4页（和第10页）把页眉标成了 `raw_label=text`，但在第2页标对了 `header`。管道**完全依赖 OCR 的 `raw_label` 做页眉排除**：

- `raw_label=header` → line 1296 route → `noise` ✅（第2页工作正常）
- `raw_label=text` → 进入 text label 路径（line 1343），经过一系列 body 启发式检查 → `body_paragraph`

没有任何内容层面的兜底检测。

正文全大写短文本在页面顶部区域所触发的对照检查：

| 信号 | 有没有 | 触发条件 |
|------|--------|---------|
| ALL-CAPS 检测 | ❌ | text path 无全大写检查 |
| 页面顶部（top 15%） | ❌ | text path 无 y 位置检查 |
| 跨页重复 | ❌ | pipeline 不比较跨页文本 |
| 行长 vs 栏宽 | ❌ | 页眉短于正常正文宽度的 50% |

### 修法（一行改动，<1h）
在 `assign_block_role` 的 `raw_label == "text"` 分支（`ocr_roles.py:~1343`）中，增加一个基于内容的页眉检测：

```
条件：
  text.isupper()
  AND len(text) < 100
  AND y_top < page_height * 0.15
  AND block_width < page_width * 0.5 (比正常正文窄)
→ role=noise, confidence=0.9
```

---

## P2#5: 多栏页 ref 排序错乱 — ✅ 已修

### 现象
2HEUD5P9 第23-26页多栏引用：refs 按列阅读顺序（左栏 top→bottom → 右栏 top→bottom）出现，不是按编号排序。

### 修复
`raw_label=reference_content` 做 primary signal（F12）的副产物。延续页上的 ref 之前丢失了 `reference_item` role，在 `skip_section_grouping` 中不参与编号排序。修正后全部正确识别并按编号排序。

验证：2HEUD5P9 ref [1]-[188] 完全按编号升序排列。
