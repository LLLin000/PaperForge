---
name: pf-deep
description: Complete three-pass deep reading of an academic paper (Keshav method). Requires OCR fulltext. Searches by Zotero key, title, DOI, or PMID.
allowed-tools: [Read, Bash, Edit]
---

# <prefix>pf-deep

## Purpose

基于单篇论文的组会式精读入口。

1. 解析 `<prefix>pf-deep <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero 并锁定单篇论文
4. 绑定该论文对应的：
   - `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md`
   - `<system_dir>/PaperForge/ocr/<KEY>/meta.json`
   - `<resources_dir>/<literature_dir>/.../KEY - Title.md`
5. 在正式文献卡片中检查或创建 `## 精读`
6. 以"研究思路 + figure-by-figure"方式一次性完成精读写回

## CLI Equivalent

```bash
# 准备阶段（间接）
python .opencode/skills/pf-deep/scripts/ld_deep.py prepare --vault "<VAULT_PATH>" --key <ZOTERO_KEY>
# 返回 JSON：{status, formal_note, fulltext_md, figures, tables}
```

> `<prefix>pf-deep` 是 **Agent 层命令**，通过 Python 代码自动检测论文状态，无需先行 CLI 准备。

## Detection（自动检测，无需手动 sync）

启动时，Agent 执行以下 Python 检测命令，代码会自动判断是否需要精读：

```bash
python .opencode/skills/pf-deep/scripts/ld_deep.py prepare --vault "<VAULT_PATH>" --key <ZOTERO_KEY>
```

返回 JSON：
- `status: "ok"` → 就绪，可以开始精读
- `status: "error"` → 被阻塞（`message` 说明原因：analyze=false / OCR 未完成 / 未找到论文）

Agent 根据返回的 `status` 决定是否进入精读流程，不自行读取 frontmatter。

**队列模式**（无参数时自动检测）：Agent 运行：
```bash
python .opencode/skills/pf-deep/scripts/ld_deep.py queue --vault "<VAULT_PATH>"
```
代码自动扫描 canonical index 中 `analyze=true` 且 `deep_reading_status=pending` 的论文，按 OCR 状态分组。

## Arguments

| 参数 | 必需 | 说明 |
|------|------|------|
| `<query>` | 是（queue 模式除外） | Zotero key、标题片段、DOI、PMID 或关键词 |
| `queue` | 否 | 启动批量精读队列模式 |

### 参数说明

1. 如果输入看起来像 8 位 Zotero key，则直接按 key 解析。
2. 否则先在本地 Zotero 中搜索标题/摘要。
3. 若命中唯一结果或明显最佳结果，则直接载入。
4. 若存在多个合理候选，则先列候选清单再让用户选。
5. 不要强迫用户先知道 Zotero key。

## Example

### 单篇精读（已知 key）

```bash
<prefix>pf-deep XGT9Z257
<prefix>pf-deep Predictive findings on magnetic resonance imaging
<prefix>pf-deep 10.1016/j.jse.2018.01.001
```

### 无参数：自动检测队列

```bash
<prefix>pf-deep
```

当不提供具体 key/标题时，agent 自动检测精读队列：

1. 运行 `python .opencode/skills/pf-deep/scripts/ld_deep.py queue --vault "<VAULT_PATH>"` 扫描队列
2. 解析输出的 JSON，按 OCR 状态分组展示
3. 由用户选择篇目

无需先跑 `paperforge sync`。

## Output

Agent 在正式笔记中创建或更新 `## 精读` 区域，包含：

- **Pass 1: 概览** — 一句话总览、5 Cs 快速评估、Figure 导读
- **Pass 2: 精读还原** — Figure-by-Figure 解析、Table-by-Table 解析、关键方法补课、主要发现与新意
- **Pass 3: 深度理解** — 假设挑战与隐藏缺陷、结论扎实性评估、Discussion 解读、个人启发、遗留问题

## Error Handling

### OCR 未完成
- **表现**：Agent 提示 `ocr_status` 不是 `done`
- **解决**：先运行 `paperforge ocr`，确认 `meta.json` 中 `ocr_status` 变为 `done`

### 内容已存在（覆盖确认）
- **表现**：正式笔记中已存在 `## 精读` 区域且包含非占位符的实质内容
- **处理**：Agent **必须**询问用户：追加 / 覆盖 / 跳过

### 未找到论文
- **表现**：Zotero key 无效或搜索无结果
- **解决**：确认 key 正确，或尝试用标题片段搜索

## 精读结构参考

### 执行原则

- `<prefix>pf-deep` 对用户来说是一次触发直接完成。
- 内部逻辑分两步：
  1. 先生成 `## 精读` 骨架和 figure 标题位
  2. 再补全所有空段
- 后续再次运行时（用户选择追加）：
  - 只补空段，不覆盖已有内容

### 精读定位

这不是综述提取，也不是信息摘录。目标是模拟高水平博士/博士后组会讲解单篇论文的学习型精读。

主线必须是：

1. 文章整体研究思路
2. 主文 figure 逐张解析
3. 关键方法补课
4. 主要发现、新意、疑点与启发

### Supplementary 规则

- 默认不逐张展开 supplementary figure/table。
- 仅在以下情况下纳入：
  - 对主结论形成关键支撑
  - 补足方法可信度
  - 限制主文结论的解释范围
  - 作者在正文中明显依赖该补充材料

### 标准骨架

```md
## 精读

**证据边界**：区分三层信息：`论文结果`、`作者解释`、`我的理解/推断`。

### Pass 1: 概览

**一句话总览**
（待补充）

**5 Cs 快速评估**
- **Category**（类型）：
- **Context**（上下文）：
- **Correctness**（合理性初判）：
- **Contributions**（贡献）：
- **Clarity**（清晰度）：

**Figure 导读**
- 关键主图：
- 证据转折点：
- 需要重点展开的 supplementary：
- 关键表格：

### Pass 2: 精读还原

#### Figure-by-Figure 解析
（每张 figure 下方按以下顺序填写）
- **图像定位与核心问题**：页码 + 要回答什么问题
- **方法与结果**：方法 + 结果
- **作者解释**：作者对该图的解读
- **我的理解**：自己的理解（区分于作者解释）
- **在全文中的作用**：该图在整体故事线中的位置
- **疑点 / 局限**：读图时发现的疑问

#### Table-by-Table 解析
（如有重要表格，按同样结构展开）

#### 关键方法补课
- 方法 1：
- 方法 2：

#### 主要发现与新意
**主要发现**
- 发现 1：
- 发现 2：

### Pass 3: 深度理解

#### 假设挑战与隐藏缺陷
- 隐含假设：
- 如果放宽某个假设，结论还成立吗？
- 缺少哪些关键引用？
- 实验/分析技术的潜在问题：

#### 哪些结论扎实，哪些仍存疑
**较扎实**
-

**仍存疑**
-

#### Discussion 与 Conclusion 怎么读
- 作者真正完成了什么：
- 哪些地方有拔高：
- 哪些地方是推测：

#### 对我的启发
- 研究设计上：
- figure 组织上：
- 方法组合上：
- 未来工作想法：

#### 遗留问题
**遗留问题**
-
```

### Figure 节要求

每个 figure 小节按以下顺序填写：

- **图像定位与核心问题**：页码 + 要回答什么问题
- **方法与结果**：方法 + 结果
- **作者解释**：作者对该图的解读
- **我的理解**：自己的理解（区分于作者解释）
- **在全文中的作用**：该图在整体故事线中的位置
- **疑点 / 局限**：读图时发现的疑问（可酌情用 `> [!warning]` 突出）

## See Also

- [pf-paper](pf-paper.md) — 快速摘要与问答
