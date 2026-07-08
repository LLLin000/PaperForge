# Dense Composite Parent Candidate Hardening Design

> **Date:** 2026-06-23
> **Status:** Proposed
> **Scope:** 只增强 dense composite page 上的 `composite_parent` 候选构造能力，不改变 ordinary same-page arbitration、sidecar 路径、persisted bucket 契约，也不引入新的 direct settlement path。

---

## 1. 为什么要单独开这个 spec

当前分支里的 `composite_parent` 已经不是纯诊断 seam，而是一个**真实参与 ownership 的 producer**。

证据已经很清楚：

1. `2UIPV93M` page 18 已经能产出 `settlement_type="composite_parent"`
2. `VFS8CBW2` page 31/32/39/41 则完全产不出可用 parent candidate
3. 因而当前瓶颈不是 arbitration 是否允许 parent 胜出，而是：

```text
dense fragmented page 上，parent candidate 根本没有被稳定构造出来
```

所以这里必须先把问题切窄：

```text
先修 candidate construction
再谈 parent arbitration
```

这个 spec 的目标不是解决全部 `VFS8CBW2` ownership，而是先让系统在这类页面上**看见**候选 parent。

---

## 2. 当前问题的真实形态

`VFS8CBW2` 暴露的是下面这条链：

```text
一个大 composite figure
-> 被拆成很多 media_asset / figure_asset / panel-title text
-> ordinary local matcher 只抓住一小块
-> 大量剩余碎片变成 unresolved_clusters
-> 个别 caption 再被 sequence_match 壳子补编号
```

这不是 sidecar overwrite 主导的问题。

这也不是单纯 Chinese / OCR 文本识别问题。

这是一个更具体的 candidate-generation 缺口：

```text
系统现在能稳定构造 atomic groups
但不能在 dense composite page 上把这些 fragments 提升成 scoped parent candidate
```

---

## 3. 本 spec 不做什么

为了防止又长出新的 ad hoc path，这个 spec 明确排除以下内容：

1. **不** 新增 `settlement_type`
2. **不** 改 sidecar 逻辑
3. **不** 改 current persisted buckets（`matched_figures` / `ambiguous_figures` / `unresolved_clusters` 等）
4. **不** 通过放宽 `_cluster_semantic_page_assets()` 阈值来把整页直接 mega-merge
5. **不** 用 paper id / page id / literal string 黑名单硬编码 `VFS8CBW2`
6. **不** 在这一轮直接重排 parent vs ordinary same-page arbitration
7. **不** 把 dense parent candidate 塞回 ordinary `candidate_groups`

一句话：

```text
这里只增强“能不能构造出 parent candidate”，不增强“谁最后赢”。
```

---

## 4. 与现有架构的关系

本 spec 必须服从两份上游文档：

1. `docs/superpowers/specs/2026-06-23-ocr-visual-grammar-hardening-design.md`
2. `docs/superpowers/specs/2026-06-23-figure-ownership-arbitration-convergence-design.md`

关系如下：

### 4.1 对 visual-grammar hardening 的位置

它相当于把原先 `P1A` 里“diagnostic-only composite parent detector”这件事切得更具体。

也就是说：

```text
这不是新的大路线
而是对 P1A 的一次收窄和落地约束
```

### 4.2 对 convergence 的位置

它属于 Layer 2 candidate generation，而不是 Layer 3 arbitration。

因此必须满足 convergence 约束：

1. visual-only construction
2. separate from ordinary `candidate_groups`
3. dense parent 作为 `composite_parent` 的 subtype，而不是新 family

允许的表达方式仍然是：

```python
{
    "group_type": "composite_parent",
    "parent_subtype": "dense_composite",
    ...
}
```

---

## 5. 设计目标

本轮只追求三个目标：

### 5.1 让 dense page 稳定地产生 parent candidate

对于 `VFS8CBW2` 这类页面，系统应该至少能产出 audit-visible 的 `composite_parent_candidates`，而不是完全没有 parent candidate。

### 5.2 不伤 ordinary page

普通双图页、普通 caption-below 页、已经稳定的 same-page figure 页，不应因为这次增强而被错误合并。

### 5.3 给后续 arbitration 提供可用输入

候选需要包含足够的信息，让后续阶段判断：

1. coverage 是否显著提升
2. 是否跨越别的 numbered caption boundary
3. 是否只是 page-wide scatter 而不是 scoped composite

---

## 6. 新的 candidate construction 思路

### 6.1 不改变 atomic grouping 的职责

`atomic semantic groups` 继续保持“局部视觉事实”的角色。

它的职责是：

```text
我能确定哪些小块在局部上属于一起
```

它**不**负责：

```text
整页 dense composite parent 的最终组织
```

所以本 spec 不允许把 dense-page 需求反向压回 atomic grouping 阈值。

### 6.2 dense parent candidate 的输入

构造输入允许来自：

1. existing atomic `candidate_groups`
2. 同页 `unresolved_clusters` 的几何信息
3. 同页 figure-like assets 的 envelope statistics
4. 同页 structured blocks 中的正文/表格/section interruption 信息

不允许作为 construction-time 输入的：

1. caption 文本编号本身
2. legend 文本语义
3. arbitration 之后才知道的 coverage truth

### 6.3 dense page trigger

只有页面满足下列条件时，才进入 dense parent candidate construction：

1. 同页存在至少一个 formal numbered figure caption
2. 同页 figure-like visual fragments 数量较高，例如 `>= 4`
3. 同页 atomic groups + unresolved clusters 共同显示出明显碎片化
4. 这些 fragments 在局部包络内足够紧凑，而不是整页散落

目标是区分：

```text
true dense composite page
vs
ordinary multi-figure page
```

---

## 7. Dense Parent Candidate Contract

本轮生成的 candidate 至少要带这些字段：

```python
{
    "group_id": str,
    "group_type": "composite_parent",
    "parent_subtype": "dense_composite",
    "page": int,
    "child_group_ids": list[str],
    "unresolved_cluster_ids": list[str],
    "asset_block_ids": list[str],
    "embedded_text_block_ids": list[str],
    "cluster_bbox": list[float],
    "fragment_count": int,
    "atomic_child_count": int,
    "unresolved_child_count": int,
    "visual_mass": float,
    "compactness": float,
    "grid_score": float,
    "construction_reason": list[str],
    "crosses_caption_boundary": bool,
    "ownership_enabled": False,
}
```

说明：

### 7.1 `ownership_enabled` 必须继续为 `False`

因为这一轮只解决 candidate construction，不直接把它升级成更激进的 live arbitration。

### 7.2 `unresolved_cluster_ids` 必须显式记录

这是本轮最重要的新信息之一。

如果一个 dense parent candidate 无法说明自己吸收了哪些 unresolved visual mass，那么它对后续 arbitration 的价值就不够。

### 7.3 `embedded_text_block_ids` 先允许为空

这一轮不要求彻底解决 panel-title suppression 与 parent consumption 的绑定。
但 contract 上要给这个槽位留出来，避免后面又生出并行结构。

---

## 8. Construction-Time Scoring Signals

这里说的是**构造候选时**可以使用的视觉信号，不是最终 arbitration score。

允许信号：

1. fragment count
2. unresolved child count
3. bbox compactness
4. row/column grid regularity
5. child bbox size similarity
6. page-local visual mass density
7. body/table interruption absence

禁止信号：

1. caption 文本内容
2. “这个 caption 解释得好不好”
3. same-page ownership 之后剩多少已确认 solved mass

原因很简单：

```text
这一层必须仍然是 visual-only construction
```

---

## 9. 与 panel-title suppression 的边界

panel-title suppression 是支持性约束，但不是本 spec 的主修复，也不是这个 ticket 的实现目标。

本 spec 只要求 candidate construction **能够容忍** 这些短文本存在，而不是依赖 suppression 先彻底清空页面。

实现边界：

```text
本 ticket 可以读取已经存在的 suppression 结果，
但不得为了让 dense parent candidate 通过而新增或重写 suppression 规则。
```

因此这里的边界是：

1. dense parent construction 不应因为存在短 panel-title text 就完全失效
2. 若页面同时存在 numbered legend 与短 panel-title candidates，dense parent construction 仍应依据 visual fragments / unresolved clusters 自身成立
3. suppression 负责减少 caption 竞争；parent construction 负责恢复 visual object

换句话说：

```text
suppression 是减噪
parent construction 是补 object
```

两者不要互相替代。

---

## 10. 成功标准

这轮不要求直接“解决 VFS8CBW2 所有 ownership”。

它的成功标准应该更窄：

### 10.1 候选可见性

`VFS8CBW2` page 31/32/39/41 这类 dense composite pages 上，`figure_inventory` 中必须能看到 audit-visible 的 `composite_parent_candidates`，而不是空。

### 10.2 不污染 ordinary pages

`2UIPV93M`、`3FDT9652`、`24YKLTHQ` 这类当前已部分稳定的普通/混合页面，不能因为 dense parent construction 扩张而出现 page-wide mega-merge。

### 10.3 unresolved mass 纳入 parent 候选视野

候选必须明确吸收部分 unresolved cluster 作为 parent construction input，而不是继续只盯着已成形 atomic groups。

### 10.4 不新增 settlement path

任何结果都仍然应该通过现有 arbitration/ownership path 落地，而不是偷偷长出 `dense_parent_settlement` 或类似新分支。

---

## 11. 最低测试要求

至少应覆盖下面几类：

1. `dense page emits composite parent candidates`
   - dense multi-panel synthetic page
   - ordinary local same-page matcher只能抓到部分
   - 仍应产生 `composite_parent_candidates`

2. `ordinary multi-figure page does not emit page-wide parent`
   - 两个独立 numbered figures 同页
   - 不得因为 fragment 数量上来就误造 dense parent

3. `dense candidate may include unresolved cluster ids`
   - unresolved visual mass 必须进入 candidate contract

4. `panel-title noise does not prevent candidate construction`
   - 即使同页有短 panel-title-like text，candidate 仍可构造
   - 这里测试的是 candidate construction 的鲁棒性，不是 suppression 新行为

5. `current working paper remains stable`
   - 至少校验 `2UIPV93M` page 18 不回退

---

## 12. Stop Condition

如果实现过程中发现必须做下面任何一件事，说明 scope 已经越界：

1. 放宽 atomic grouping 阈值去吞整页
2. 引入新的 direct settlement type
3. 依赖 literal label blacklist
4. 必须重写 sidecar
5. 必须重排 entire arbitration precedence

一旦出现这些信号，应停止实现，回到上层 spec/plan 重新切分。

---

## 13. 结论

当前分支的 `composite_parent` 不是不存在，而是：

```text
已经 live
但 candidate construction 对 dense fragmented pages 还不够强
```

因此下一步不应直接做更大的 dense arbitration rollout，
而应先完成：

```text
dense composite parent candidate hardening
```

把 `VFS8CBW2` 这类页面从“根本看不见 parent”推进到“至少稳定地产生可审计 parent candidate”，
后续再谈谁在 arbitration 里最终胜出。
