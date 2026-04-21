# Subagent Prompt for /LD-deep

## 任务

对指定论文完成 journal-club 风格的精读（基于 Keshav 三阶段阅读法），写入正式文献笔记的 `## 🔍 精读` 区域。

## 输入变量（由主 agent 填入）

- `{{ZOTERO_KEY}}` — Zotero key，如 `Y5KQ4JQ7`
- `{{FORMAL_NOTE}}` — 正式笔记完整路径，如 `D:\L\Med\Research\03_Resources\Literature\骨科\Y5KQ4JQ7 - Title.md`
- `{{FULLTEXT_MD}}` — OCR 全文本路径，如 `D:\L\Med\Research\99_System\LiteraturePipeline\ocr\Y5KQ4JQ7\fulltext.md`
- `{{SCRIPT}}` — `D:\L\Med\Research\.opencode\skills\literature-qa\scripts\ld_deep.py`

## 正确流程（必须按顺序执行）

### 第一步：Figure Map 预扫描（Agent 执行）

不要自己猜 figure 编号。运行 figure-map 命令，让脚本基于 caption 解析所有图表：

```
python {{SCRIPT}} figure-map "{{FULLTEXT_MD}}" --key {{ZOTERO_KEY}} --out "D:\L\Med\Research\99_System\LiteraturePipeline\ocr\{{ZOTERO_KEY}}\figure-map.json"
```

读取生成的 `figure-map.json`，获得结构化清单：
- `figures`: 主文 figure（Figure 1, 2, 3...）
- `tables`: 主文 table（Table 1, 2...）
- `supplementary_figures`: 补充图（Supplementary Figure S1...）
- `supplementary_tables`: 补充表（Supplementary Table S1...）

基于清单判断：
- **主图**：默认全部展开（Figure 1-N）
- **主表**：只展开有核心数据的表（ demographics、结果汇总、统计对比等）
- **补充材料**：仅当对主结论形成关键支撑、补足方法可信度、或限制主文解释范围时才展开

记录选定的 figure/table 编号（用 `image_id` 而非 caption 数字）。

### 第二步：创建/更新骨架

**输入变量**：`{{MODE}}` — 主 agent 传入的模式，可选值：`append`（默认，追加/补充）、`overwrite`（覆盖重写）。

**若 MODE == `overwrite`**：
1. 先删除现有 `## 🔍 精读` 区域：读取 `{{FORMAL_NOTE}}`，找到 `## 🔍 精读` heading，删除从该行开始到下一个同级（`## `）或更高级 heading 之前的所有内容。
2. 将删除后的内容写回 `{{FORMAL_NOTE}}`。
3. 然后运行 `ensure-scaffold` 生成全新骨架：
   ```
   python {{SCRIPT}} ensure-scaffold "{{FORMAL_NOTE}}" --fulltext "{{FULLTEXT_MD}}" --figures "<image_id1>,<image_id2>,..." --tables "<image_id1>,..."
   ```

**若 MODE == `append` 或未指定**：
- 如果 `## 🔍 精读` 已存在且包含实质内容（非纯占位符），跳过骨架生成，直接进入第三步补充空缺。
- 如果不存在或只有空骨架，运行上述 `ensure-scaffold` 命令生成骨架。

如果 figure 解析失败，骨架里会显示"暂未从 OCR 中解析到可用主图"，这是正常的，继续填写其他内容。

### 格式规范（强制）

**Callout 间距规则**：在 Obsidian 中，连续的 callout 块如果没有空行分隔，会被合并成一个块。必须遵守以下规则：

1. **不同 callout 之间必须有空行**：
   ```markdown
   > [!warning] 第一个警告
   > 内容

   > [!warning] 第二个警告
   > 内容
   ```

2. **同一类型的多个 callout 之间也必须有空行**：
   ```markdown
   > [!question] 遗留问题 1
   > 问题描述

   > [!question] 遗留问题 2
   > 问题描述
   ```

3. **Figure/Table callout 之间也必须有空行**（骨架已自动处理，agent 补充时同理）。

**错误示例**（会导致合并）：
```markdown
> [!warning] 警告1
> [!warning] 警告2
```

**正确示例**：
```markdown
> [!warning] 警告1
> 内容

> [!warning] 警告2
> 内容
```

### 第三步：三阶段精读（Keshav 法）

用 Read 工具加载 `{{FORMAL_NOTE}}`，找到 `## 🔍 精读` 区域，按以下三阶段填写。

**注意**：三阶段可以一次调用完成，也可以分多次调用。如果内容过多，先完成 Pass 1 + Pass 2，Pass 3 可以在后续调用中补完。

#### Pass 1: 概览（第一遍，5-10 分钟）

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

#### Pass 2: 精读还原（第二遍，figure-by-figure）

逐图逐表精读，把握内容但不陷入细节。

```markdown
### Pass 2: 精读还原

#### Figure-by-Figure 解析

（每张主图按以下结构）

##### Figure N：{caption 一句话概括}
![[image_link]]

**图像定位与核心问题**
- 页码：
- 这张图要回答什么：

**方法与结果**
- 方法：（实验设计/数据来源/技术路线）
- 结果：（图中展示的核心数据点/趋势/对比）

**图表质量审查**（仅对含 graph/plot 的图执行；纯示意图跳过）
- 轴标签是否完整？单位是否标注？
- 是否有 error bars / 置信区间 / 统计显著性标记？
- 如果缺少这些，对结论可信度有什么影响？
- **[进阶]** 识别图表类型后，参考 `99_System/Template/读图指南/` 中的对应子指南进行深度审查（如箱式图看IQR与异常值、热图看标准化与批次、ROC曲线看截断点与AUC置信区间等）

**作者解释**
- 作者在文中对该图的描述：

**我的理解**
- 自己的分析（区分"作者解释"和"我的理解"）：

**在全文中的作用**
- 该图在整体故事线中的位置：

**疑点 / 局限**
- （可酌情用 `> [!warning]` 突出）

#### Table-by-Table 解析

（每张重要表格按以下结构）

##### Table N：{caption 一句话概括}
![[image_link]]

- 这张表在回答什么问题：
- 关键字段 / 分组：
- 主要结果：
- 我的理解：
- 在全文中的作用：
- 疑点 / 局限：

#### 关键方法补课
- 方法 1：（如有不熟悉的实验技术，简要补课）
- 方法 2：

#### 主要发现与新意
**主要发现**
- 发现 1：（证据来源：Figure X / Table Y）
- 发现 2：
```

#### Pass 3: 深度理解（第三遍，质疑与迁移）

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

### 第四步：callout 使用规则

骨架是纯文本，填写时选择性使用 callout 突出重要信息：
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

### 第五步：验证骨架完整性

完成后，运行：

```
python {{SCRIPT}} validate-note "{{FORMAL_NOTE}}" --fulltext "{{FULLTEXT_MD}}" --figures "<image_ids>"
```

如果输出不是 `OK`，说明有缺失的 section headings 或 figure embeds，需要修复后再报完成。

### 错误处理

- 如果 `fulltext.md` 不存在或为空：立即报错，说明"OCR 文件不存在：{{FULLTEXT_MD}}"，不要静默继续
- 如果 `figure-map` 报错：把完整错误信息报告给主 agent
- 如果 `ensure-scaffold` 报错：把完整错误信息报告给主 agent
- 如果 `validate-note` 失败：列出缺失项目并修复。**注意**：`validate-note` 现在会检查 callout 间距问题——如果多个 `> [!warning]` / `> [!question]` / `> [!note]-` 之间缺少空行，会报告 spacing 错误。修复方法：在相邻 callout 之间插入空行。

## 交付要求

1. 骨架创建/更新成功后，必须报告：写入行数、figure 数量、包含的 section 列表
2. 所有内容填写完毕后，运行 validate-note 并报告结果
3. 如有任何异常（包括 figure 解析失败、路径找不到等），必须报告完整错误信息，不要静默跳过
4. 只写回 `{{FORMAL_NOTE}}`，不要写其他文件

## 参考：ld_deep.py 命令速查

```bash
# 生成 caption-driven figure map
python {{SCRIPT}} figure-map "{{FULLTEXT_MD}}" --key {{ZOTERO_KEY}} --out "D:\L\Med\Research\99_System\LiteraturePipeline\ocr\{{ZOTERO_KEY}}\figure-map.json"

# 创建/更新骨架（指定 image_id）
python {{SCRIPT}} ensure-scaffold "{{FORMAL_NOTE}}" --fulltext {{FULLTEXT_MD}} --figures "<id1>,<id2>"

# 验证骨架完整性
python {{SCRIPT}} validate-note "{{FORMAL_NOTE}}" --fulltext {{FULLTEXT_MD}} --figures "<id1>,<id2>"
```
