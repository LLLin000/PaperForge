# Subagent Prompt for /pf-deep

## 任务

对指定论文完成 journal-club 风格的精读（基于 Keshav 三阶段阅读法），写入正式文献笔记的 `## 🔍 精读` 区域。

## 输入变量（由主 agent 填入）

- `{{ZOTERO_KEY}}` — Zotero key，如 `Y5KQ4JQ7`
- `{{VAULT}}` — Vault 根路径
- `{{SCRIPT}}` — `<Vault>/<skill_dir>/literature-qa/scripts/ld_deep.py`

## 正确流程（必须按顺序执行）

### 第一步：一键前置准备（运行 prepare 命令）

**这是唯一需要运行的机械化命令**。它会自动完成：检查状态、生成 figure-map、扫描图表类型、插入骨架。

```
python {{SCRIPT}} prepare {{ZOTERO_KEY}} --vault "{{VAULT}}" --format text
```

**期望输出示例**：
```
[OK] Prepared Y5KQ4JQ7
  Formal note: Y5KQ4JQ7 - Title.md
  Figures: 6 | Tables: 2
  Chart guides: 5 recommended
```

**如果输出以 `[ERROR]` 开头**：
- 立即停止，将错误信息报告给主 agent
- 常见错误：analyze != true（需用户在 Base 中勾选 analyze）、OCR 未完成、formal note 不存在

**如果输出 `[WARN] deep_reading_status already 'done'`**：
- 这说明该论文已经精读过。如果用户要求重新精读，通知主 agent 确认是否覆盖。

**prepare 成功后会自动生成以下文件**：
- `<system_dir>/PaperForge/ocr/{{ZOTERO_KEY}}/figure-map.json` — 图表清单
- `<system_dir>/PaperForge/ocr/{{ZOTERO_KEY}}/chart-type-map.json` — 图表类型与推荐指南

**Agent 需要读取 chart-type-map.json**，为每张 figure 建立 `chart_types` 备忘列表。在 Pass 2 解析该 figure 时，根据其 chart_types 读取 `{{CHART_READING_DIR}}` 下对应的 chart-reading 指南，将关键审查问题整合进"图表质量审查"段落。

> **注意**：prepare 命令已自动在 formal note 中插入了 `## 🔍 精读` 骨架（包含所有 figure/table 的 callout 块）。Agent **不需要**再手动运行 ensure-scaffold。

---

### 第二步：Pass 1 概览（单独执行，完成后保存）

**执行策略**：Pass 1 只填写 `### Pass 1: 概览` 区域，不要碰 Pass 2/3 的内容。

用 Read 工具加载 formal note（路径在 prepare 输出中），找到 `## 🔍 精读` 区域，定位到 `### Pass 1: 概览`，将占位符替换为实际内容。

快速扫描，建立全局认知，决定是否值得深入。

```markdown
### Pass 1: 概览

**一句话总览**
（论文类型 + 核心贡献一句话，如：这是一项关于XX的前瞻性队列研究，核心发现是YY。）

**5 Cs 快速评估**
- **Category**（类型）：这是什么类型的论文？测量/分析/原型/方法学/综述/临床试验/队列研究/病例系列？
- **Context**（上下文）：基于哪些理论或前人工作？与哪些论文直接相关？理论基础是什么？
- **Correctness**（合理性初判）：作者的假设看起来合理吗？样本量/研究设计是否匹配研究问题？（第一遍只做直觉判断，后续 Pass 3 深入质疑）
- **Contributions**（贡献）：明确列出 1-3 个主要贡献。
- **Clarity**（清晰度）：论文结构是否合理？写作是否清晰？图表是否自明？

**Figure 导读（快速扫图，仅列编号 + 一页纸猜测）**
- 关键主图：Figure 1（猜测：XXX）、Figure 2（猜测：YYY）...
- 证据转折点：预计 Figure X 是核心结论的支撑
- 需要重点展开的 supplementary：（如有）
- 关键表格：Table X（猜测：ZZZ）
```

**完成后**：用 Edit 工具将填写好的 Pass 1 内容写回 formal note，保存。然后继续下一步。

---

### 第三步：Pass 2 精读还原（分块执行，每块完成后保存）

**执行策略**：Pass 2 只填写 `### Pass 2: 精读还原` 区域。内容量大，必须分块执行，不要试图一次写完全部 figure。

#### 分块规则

将 figure/table 分为 2-3 个一组的块：
- 第 1 块：Figure 1-2（或 1-3）
- 第 2 块：Figure 3-4（或 4-5）
- 第 3 块：剩余 Figure + Table + 关键方法补课 + 主要发现与新意

每完成一个块，**立即用 Edit 保存**，然后 Read 确认已写入，再继续下一个块。

#### Figure-by-Figure 解析（逐块填写）

每张主图按以下结构：

```markdown
##### Figure N：{caption 一句话概括}
![[image_link]]

**图像定位与核心问题**
- 页码：
- 这张图要回答什么：

**方法与结果**
- 方法：（实验设计/数据来源/技术路线）
- 结果：（图中展示的核心数据点/趋势/对比）

**图表类型识别与 chart-reading 引用（强制）**
1. **识别子图类型**：基于 caption 和图像内容，列出该 figure 包含的所有图表子类型（如：柱状图、折线图、免疫荧光图、热图等）
2. **读取 chart-reading 参考**：根据 prepare 生成的 chart-type-map.json 中该 figure 的 `recommended_guides`，读取对应指南文件
3. **执行审查清单**：将 chart-reading 指南中的核心审查问题逐条应用到该 figure 上，至少回答以下问题：
   - 如果是**柱状图/条形图**：Y轴是否从0开始？误差棒类型是SD/SEM/CI？是否进行了多重比较校正？
   - 如果是**折线图/时间序列**：曲线是否符合某种动力学模型？是否达到平台期？突释效应如何？
   - 如果是**免疫荧光图**：是否使用 sequential scanning？荧光强度定量方法是什么？背景阈值如何设定？
   - 如果是**热图/聚类图**：标准化方法是什么（Z-score/log/percentile）？聚类算法和距离度量是什么？是否存在循环论证？
   - 如果是**火山图**：显著性阈值是raw p-value还是FDR？效应量阈值是多少？上调/下调是否对称？
   - 如果是**MSEA/GSEA富集图**：q值阈值是多少（0.25还是0.05）？基因集大小是否合理？Leading Edge占比多少？
   - 如果是**弦图/网络图**：弦的粗细代表什么？是否过度解读了方向性？
   - 如果是**组织学图**：评分系统是什么？是否盲法评分？评分者间一致性（ICC/κ）是否报告？
   - 如果是**箱式图/小提琴图**：中位数、IQR、异常值如何？组间分布是否对称？
   - 如果是**散点图/气泡图**：相关性系数是多少？是否进行了回归分析？R²值如何？
   - 如果是**ROC曲线**：AUC是多少？置信区间是否报告？截断点如何选择？
   - 如果是**生存曲线**：中位生存期是多少？HR和置信区间是否报告？删失数据如何处理？
4. **整合审查结果**：将上述审查的发现写入下方的 "**图表质量审查**" 段落。如果某条审查不适用，明确标注"N/A"；如果审查发现问题，用 `> [!warning]` 标出。

**图表质量审查**
- 轴标签是否完整？单位是否标注？
- 是否有 error bars / 置信区间 / 统计显著性标记？
- 根据 chart-reading 指南执行后的额外发现：
- 如果缺少这些，对结论可信度有什么影响？

**作者解释**
- 作者在文中对该图的描述：

**我的理解**
- 自己的分析（区分"作者解释"和"我的理解"）：

**在全文中的作用**
- 该图在整体故事线中的位置：

**疑点 / 局限**
- （可酌情用 `> [!warning]` 突出）
```

#### Table-by-Table 解析

每张重要表格按以下结构：

```markdown
##### Table N：{caption 一句话概括}
![[image_link]]

- 这张表在回答什么问题：
- 关键字段 / 分组：
- 主要结果：
- 我的理解：
- 在全文中的作用：
- 疑点 / 局限：
```

#### 关键方法补课
- 方法 1：（如有不熟悉的实验技术，简要补课）
- 方法 2：

#### 主要发现与新意
**主要发现**
- 发现 1：（证据来源：Figure X / Table Y）
- 发现 2：

**完成后**：确保 Pass 2 所有内容都已保存到 formal note，然后继续下一步。

---

### 第四步：Pass 3 深度理解（基于已写内容，完成后保存）

**执行策略**：Pass 3 填写 `### Pass 3: 深度理解` 区域。这是基于前两个 pass 已写入内容的总结与升华，可以引用 Pass 1/2 中的具体发现。

对医学文献，Pass 3 的核心不是"复现"，而是**批判性评估 + 临床/研究迁移**。可以 spawn 多个 subagent 并行分析不同维度，最后整合。

**并行分析维度（可选，根据论文类型选择 2-3 个）：**

1. **临床证据质量评估**：循证医学视角（PICO、偏倚风险、证据等级）
2. **方法学审查**：统计方法、实验设计、样本量、对照设置
3. **领域上下文对比**：与当前领域最新进展的关系，是否被后续研究验证或推翻
4. **研究迁移思考**：如果把这个方法/结论用到我的课题上，需要什么条件？最大障碍是什么？

```markdown
### Pass 3: 深度理解

#### 假设挑战与隐藏缺陷
- **隐含假设**：（作者未明说但依赖的假设，如"样本代表性""测量无偏""模型线性"）
- **如果放宽某个假设，结论还成立吗？**
- **缺少哪些关键引用？**（相关工作是否充分对比？）
- **实验/分析技术的潜在问题**：（样本量、对照组、盲法、统计方法选择、混杂因素控制）

#### 哪些结论扎实，哪些仍存疑
**较扎实**
- ...

**仍存疑**
- ...

#### Discussion 与 Conclusion 怎么读
- 作者真正完成了什么：
- 哪些地方有拔高：
- 哪些地方是推测：

#### 对我的启发
- 研究设计上：
- figure 组织上：
- 方法组合上：
- **未来工作想法**：

#### 遗留问题
**遗留问题**
- ...
```

**关键提示**：Pass 3 的写作可以引用 Pass 1 的"5 Cs 评估"和 Pass 2 的"主要发现"作为基础，形成连贯的批判性分析。不要孤立地写 Pass 3。

**完成后**：用 Edit 保存，然后进入验证步骤。

---

### 第五步：Callout 使用规则

填写时选择性使用 callout 突出重要信息：
- **主要发现**的每条 → `> [!important]`
- **仍存疑**的每条 → `> [!warning]`
- **遗留问题** → `> [!question]`
- **证据边界说明** → `> [!warning]`
- **疑点/局限** → `> [!warning]`
- 常规结构节（研究问题、路线、方法、启发等）保持普通 Markdown 列表，不用 callout

**Callout 间距强制要求**：
- 多个 `> [!important]`、`> [!warning]` 或 `> [!question]` 之间**必须有空行**，否则 Obsidian 会合并成一个 callout。
- Figure/Table 的 `> [!note]-` callout 之间也**必须有空行**。

**错误示范（太乱 + 会合并）**：
```
> [!important] 主要发现
> 发现 1：...
> 发现 2：...
> [!warning] 仍存疑
> - ...
```

**正确示范（简洁 + 有空行）**：
```
**主要发现**
> [!important] 发现 1：（文字内容）

> [!important] 发现 2：（文字内容）

**仍存疑**
> [!warning] - 某结论缺乏独立验证
```

---

### 第六步：验证完整性

完成后，运行 validate-note 检查结构完整性：

```
python {{SCRIPT}} validate-note "<formal_note_path>" --fulltext "<fulltext_md_path>"
```

其中 `<formal_note_path>` 和 `<fulltext_md_path>` 从 prepare 的输出中获取。

如果输出不是 `OK`，说明有缺失的 section headings 或 figure embeds，需要修复后再报完成。

### 错误处理

- 如果 `prepare` 返回 `[ERROR]`：立即停止，将完整错误信息报告给主 agent
- 如果 `validate-note` 失败：列出缺失项目并修复。**注意**：`validate-note` 会检查 callout 间距问题——如果多个 `> [!warning]` / `> [!question]` / `> [!note]-` 之间缺少空行，会报告 spacing 错误。修复方法：在相邻 callout 之间插入空行。

## 交付要求

1. prepare 成功后，报告：formal note 路径、figure 数量、table 数量
2. 所有内容填写完毕后，运行 validate-note 并报告结果
3. 如有任何异常，必须报告完整错误信息，不要静默跳过
4. 只写回 formal note，不要写其他文件

## 参考：ld_deep.py 命令速查

```bash
# 一键前置准备（唯一需要 Agent 运行的机械化命令）
python {{SCRIPT}} prepare {{ZOTERO_KEY}} --vault "{{VAULT}}" --format text

# 验证骨架完整性（完成所有 Pass 后运行）
python {{SCRIPT}} validate-note "<note_path>" --fulltext "<fulltext_path>"

# 列出待精读队列（信息用）
python {{SCRIPT}} queue --vault "{{VAULT}}" --format table
```
