# OCR 问题深查报告 — Zone/Role 维度

> 2026-07-02 | 基于 500 篇 corpus 扫描 + 5 篇论文深挖

---

## P1: `(N)` 括号格式 ref 不识别

**根因**: 3 个检测点都不认 `(N)` 前缀

| 位置 | 文件 | 当前正则 | 缺失 |
|------|------|---------|------|
| `_REFERENCE_PATTERN` | `ocr_roles.py:72` | `\d+\.\s` / `et al.` | `\(\d+\)\s` |
| `_ref_number_sort_key` | `ocr_render.py:488` | `N.` / `N)` / `[N]` | `(N)` |
| `score_reference_entry.has_number_lead` | `ocr_reference_signals.py:37` | `[N]` / `N.` / `N)` / bare `N` | `(N)` |

**影响**: 30/500 篇论文 (6%) 使用 `(N)` 格式，全部受影响

**9ZIJTI6J 实例**: 506 个 `(N)` 前缀 block，496 个被标为 `backmatter_body`（语意全错）。fulltext 渲染恰好正确因为 refs 在 post_reference_backmatter_zone 里被发射了——但排序用的是 backmatter 顺序而非 ref number 顺序。

**修复方案**: 三处统一加 `\((\d+)\)` 分支

---

## P2: Cross-page ref 角色不一致

**论文**: WNDJX4KB

**现象**: 
- 前 6 条 ref（page 8，与 heading 同页）→ `body_paragraph`
- 后 20 条 ref（page 9+）→ `reference_item`
- **所有 26 条 block 的 `raw_label` 都是 `reference_content`**

**根因**: `assign_block_role` 阶段 raw_label=reference_content 正确分配 reference_item；但 `resolve_final_role` 对 page 8 的 block 没有做 zone-based 升级。这是因为 reference zone 在 heading 页（page 8）上还没完全建立（`reference_zone.status='HOLD'`），late resolution 时 zone-based 升级逻辑不生效。

**影响范围**: 跨页 ref 的 heading 页上第一条 ref 可能被 demote。发生在 heading 不在 pages[0] 位置的时候。

---

## P3: Ref 在 block 里但 fulltext 丢失

### 3a: KUR9PBJC — heading 被标成 subsection_heading

"References and Notes" 被检测为 `subsection_heading`（`body_zone`）不是 `reference_heading`。导致 `reference_zone.status='HOLD'` → fulltext 结尾只有 publisher 水印，165 条 ref 没被组装成 reference section 渲染——实际上它们以 raw LaTeX 形式出现在 fulltext 但格式不完整，且 ref 147-149、159 在渲染过程中丢失。

**根因**: "References and Notes" 的 `paragraph_title` raw_label 进入了 heading resolution 但被分类为 subsection_heading 而非 reference_heading。

### 3b: U746UJ7G — 编号 40/41/43 渲染丢失

三条 ref（40/41/43）在 block 里是 `reference_item`、`render_default=True`、在 `reference_zone`，但 fulltext 没有。可能是排序或渲染阶段的截断问题（附近有 ref 41→42→44 跳过了 43）。

---

## P4: Reference heading 完全消失 — 4 篇 Wiley 论文

**97M7HFCD、2HEUD5P9、99JVAPSV、UV6IVNUE**

### 现象
- 4 篇全部**没有任何 block 包含 "References" 文本**
- 4 篇全部来自 Wiley 出版社（Advanced Science, Small Methods, Adv. Funct. Mater., Adv. Healthcare Mater.）
- 4 篇都有几百条 reference_item 在 reference_zone（部分编号格式异常："2409400"、"2301283"、"1909045" 等——这些是 Wiley 的 article tracking number 被误判为 ref）
- `reference_zone.status` 全部是 `'HOLD'`（heading_block_id=None）
- Fulltext **完全没有 Reference 章节**

### 根因分析
Wiley 这些 PDF 的 "References" heading 可能:
1. 被 OCR 识别为 noise/header（和杂志名跑头混在一起）
2. 以图形方式嵌在 PDF 里（非文本）
3. 被 `references_start` 定位正确（page=y=0.0）但具体 block 被分类为其他 role

**核心问题**: 没有 reference_heading → pipeline 不渲染 ref section。即便有几百条 ref_items 也出不来。

### 次级问题: fake reference_item
这些论文里部分以数字开头的 text block 被 `_looks_like_reference` 误判为 reference_item（如 "2409400 (6 of 13)" 是 Wiley 的 article tracking footer，根本不是 ref）。需要在 `_looks_like_reference` 加长度/格式过滤。

---

## P5: Author bio 在 reference zone

**论文**: 4AG67PBH

### 现象
- 3 条 author bio（"is a Ph.D. student...", "is assistant professor..."）在 `reference_zone`
- role 是 `backmatter_body`（role 对了但 zone 错了）
- `backmatter_start` 正确指向 page 25（bio 所在的 page）
- 但 zone inference 没有从 reference_zone 切换到 post_reference_backmatter_zone

### 根因
`reference_zone.status='HOLD'`（无 heading）→ zone inference 不知道 reference 在哪结束。backmatter content 被留在 reference_zone 里。这和后 4 个问题是同一个源头：**reference heading 缺失导致 zone boundary 不确定。**

---

## 问题关联图

```
reference heading 不被检测
    ├─→ P2: heading 同页的 ref 得不到 zone-based 升级
    ├─→ P3: reference_zone.status=HOLD → ref section 渲染不完整
    ├─→ P4: fulltext 完全没有 Reference 章节（最严重）
    └─→ P5: zone boundary 不确定 → backmatter content 留在 ref zone
            (4AG67PBH)

(N) 格式不匹配
    └─→ P1: 6% 论文 ref 语义丢失
```

---

## 修复优先级

| Priority | Problem | Why | Fix scope |
|----------|---------|-----|-----------|
| **P0** | P4: heading 完全消失 | 4 篇论文 fulltext 没有 ref 章节，最严重 | 需要查 Wiley PDF 的 "References" heading 为什么没被识别 |
| **P1** | P1: `(N)` 格式 | 6% 语料受影响，30 篇论文，修复简单 | 3 处 regex 统一加 `\((\d+)\)` |
| **P2** | P3: ref 渲染丢失 | 影响 fulltext 完整性 | 查渲染排序逻辑 |
| **P3** | P2: cross-page ref | 少量 block 受影响，低严重性 | resolve_final_role 需要处理 heading 页 |
| **P3** | P5: bios in ref zone | 边界 case，和 P3/P4 同根因 | heading 修好了这个跟着好 |
