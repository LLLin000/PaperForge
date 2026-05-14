# deep-reading

> **Safety Rule:** Prior reading-log entries are recheck targets only, never factual answers.
> Always verify against original source before using any reading-log content.

Keshav 三阶段精读。在 formal note 中写入结构化的 `## 精读` 区域。

---

## 前置检查

### Step 0: paper-context（必须）

```bash
$PYTHON -m paperforge paper-context <zotero_key> --json --vault "$VAULT"
```

检查返回 JSON：
- `ok: false` → 报告 `error.message`，停止
- `data.paper.ocr_status != "done"` → "OCR 未完成，请先运行 paperforge ocr"，停止
- `data.paper.analyze != true` → "analyze 未开启，请在 formal note frontmatter 中设为 true"，停止

**检查 prior_notes：**
- 如果存在 `data.prior_notes`，逐条看 `verified` 字段
- `verified: false` 的条目记入 recheck_targets，精读时必须回原文复核这些位置
- `verified: true` 的条目可以信任，但标注"之前已验证"

**记录关键路径：**
- `data.paper.note_path`（formal note 路径）
- `data.paper.fulltext_path`（fulltext 路径）
- 记下 `recheck_targets` 列表

---

## 执行流程

### Step 1: Prepare（跑脚本）

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" prepare --key <zotero_key> --vault "$VAULT"
```

解析返回 JSON：
- `status: "ok"` → 记下 `figure_map`、`chart_type_map`、`formal_note`、`fulltext_md`、`figures`、`tables` 的路径和数量
- `status: "warn"` + `deep_reading_status: done` → 告知用户"该文献已精读过"，确认是否重读
- `status: "error"` → 报告 `message`，停止

读 formal note，确认 `## 精读` 骨架已插入。

---

### Step 2: Pass 1 — 概览

只填 `### Pass 1: 概览`。不碰 Pass 2/3。

填写内容必须来自原文，不可推断：

- **一句话总览**：论文类型 + 核心发现，一句话
- **5 Cs 快速评估**：
  - Category（RCT / 队列 / 综述 / 基础研究等）
  - Context（领域共识，本文要解决什么）
  - Correctness（初步直觉，逻辑有否明显漏洞）
  - Contributions（1-3 条）
  - Clarity（写作质量，图表可读性）
- **Figure 导读**（基于 fulltext 浏览各图 caption）：
  - 关键主图：列出，一句话概括要证明什么
  - 证据转折点：哪个 figure 是叙事关键转折
  - 需要重点展开的 supplementary
  - 关键表格

填完立即保存。

---

### Step 3: Pass 2 — 精读还原

填 `### Pass 2: 精读还原`。**按 figure 顺序逐个处理**。

每处理完一个 figure 立即保存。

#### 图表类型定位（两步）

**A: 读 chart-type-map**（prepare 输出中包含该路径）。这是关键词命中建议。

**B: Agent 读 caption 做最终判断**
1. 读该 figure 的 caption（来自 fulltext）
2. 打开 `references/chart-reading/INDEX.md`，对照 caption 内容判断图表类型
3. chart-type-map 建议和 Agent 判断不一致时 → 以 Agent 判断为准
4. 无法确定类型 → 跳过 chart guide，按通用结构分析
5. 确定类型 → 读对应 chart-reading 指南，按指南中的检查清单分析

#### 每张 Figure 的子标题（固定，不可跳过）

```
**图像定位与核心问题**：页码 + 要回答什么问题
**方法与结果**：实验设计 / 数据来源 / 技术手段；核心数据、趋势、对比
**图表质量审查**：按 chart-reading 指南检查坐标轴、单位、误差棒、统计标注
**作者解释**：作者在正文中对该图的解读
**我的理解**：自己的理解（必须与作者解释做明显区分）
**疑点/局限**：用 `> [!warning]` 突出
```

#### 每张 Table 的子标题（简化版）

```
回答什么问题、关键字段/分组、主要结果、我的理解、疑点/局限
```

#### 所有 figure/table 处理完后

**关键方法补课**：简要解释不熟悉的实验技术（1-2 项）

**主要发现与新意**：
- 发现 1：...（来源：Figure X）
- 发现 2：...（来源：Table Y）
- 每条发现必须标注来源（Figure 编号或正文段落）

---

### Step 4: Postprocess（跑校验，修正问题）

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" postprocess-pass2 "<formal_note_path>" --figures <N> --vault "$VAULT"
```

- 输出 `OK` → 继续 Step 5
- 输出错误列表（含行号）→ 按提示修正，修正后重新跑
- 最多 3 轮修正。3 轮后仍失败 → 报告剩余错误给用户

---

### Step 5: Pass 3 — 深度理解

填 `### Pass 3: 深度理解`。基于 Pass 1/2 已写内容。

- **假设挑战与隐藏缺陷**：隐含假设；放宽假设后结论还成立吗；缺少的关键引用；实验/分析技术潜在问题
- **哪些结论扎实，哪些仍存疑**：
  - 较扎实：...
  - 仍存疑：...（用 `> [!warning]`）
- **Discussion 与 Conclusion 怎么读**：作者实际完成了什么；哪些有拔高；哪些是推测
- **对我的启发**：研究设计、figure 组织、方法组合、未来工作
- **遗留问题**：...（用 `> [!question]`）

---

### Step 6: Final Validation

```bash
$PYTHON "$SKILL_DIR/scripts/pf_deep.py" validate-note "<formal_note_path>" --fulltext "<fulltext_path>"
```

- 输出 `OK` → 告知用户精读完成
- 输出错误 → 修正缺失项，直到通过

---

## Callout 格式规则

- `> [!important]` — 每个 main finding
- `> [!warning]` — 疑问、局限、证据边界、仍存疑条目
- `> [!question]` — 遗留问题
- **相邻 callout 之间必须有空行**（否则 Obsidian 合并）：
  - 正确：`> [!important] A\n\n> [!important] B`
  - 错误：`> [!important] A\n> [!important] B`

---

## 禁止

- 不要在 Pass 1 完成前碰 Pass 2/3
- 不要把推断写成文献事实——区分"作者说了 X"和"我推断 Y"
- 不要跨 figure 写综合判断（Pass 2 逐图，Pass 3 才做综合）
