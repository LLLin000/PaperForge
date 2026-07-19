# Pending: Caption Prefix Recovery — Multi-Column False Negative Risk

**发现于** 2026-07-02 对抗性审查

## 问题

`_recover_figure_heading_prefix()` 只检查 heading 的**下一行**（y-order immediate next）。在多列布局中，left-column heading 和 right-column body text 可能在 y 上交错，导致 "下一行" 是另一列的内容，而非 heading 自己的 caption 体。造成假阴性（prefix 恢复失败）。

## 约束

1. 不能引入硬编码 px 阈值（之前尝试过 100px，不准）
2. 不能用 "OCR block bbox 上边界" 做搜索边界——block bbox 不确定，且不是所有流程阶段都有可靠 bbox
3. 不能过度工程化——这是个 ~2% 的边缘情况

## 可能方案（待评估）

- 用 page 相对阈值（`page_height * 0.08`，跟 `_cluster_page_assets` 一致）替代硬编码 px
- 结合 column 信息：检查 next line 的 x_center 是否在 heading 的同一 column（通过 page_width/2 判断左右列）
- 不做特殊处理，接受 ~2% 的假阴性率（当前状态下 Figures 1-9 恢复成功已验证，5S7UI34M 工作正常）

## 状态

待决定是否要修以及怎么修。
