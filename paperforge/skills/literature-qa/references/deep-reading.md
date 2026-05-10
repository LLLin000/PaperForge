# 三阶段精读

Keshav 三阶段组会式精读。触发后执行以下工作流。

> **路径说明：** 本文件中的 `scripts/ld_deep.py` 相对于本 skill 目录。Agent 运行时 skill 目录由平台注入（通常为 `<installation_path>/paperforge/skills/literature-qa/`）。如不确定，AI 应从 SKILL.md 所在目录推断。

---

## 前置条件检查

执行前确认：
- [ ] 已完成论文定位（参考 [paper-resolution.md](paper-resolution.md)），拿到 zotero_key 和 workspace
- [ ] `analyze: true`（在 formal note frontmatter 中，resolver 返回的 workspace 里可查到）
- [ ] `ocr_status: done`（在 resolver 返回的 workspace 里可查到）

如果前置条件不满足，告知用户并停止。

---

## 执行流程

### Step 1: Prepare（机械操作，跑脚本）

```bash
python scripts/ld_deep.py prepare --key <ZOTERO_KEY>
```

返回 JSON 解析：
- `status: "ok"` → 记下 `figure_map`、`chart_type_map`、`formal_note`、`fulltext_md`、`figures`、`tables` 路径和数量 → 继续
- `status: "error"` → 报告 `message` 给用户，停止

读 formal note 确认 `## 🔍 精读` 骨架已插入。

---

### Step 2: Pass 1 — 概览

只填 `### Pass 1: 概览` 区域。不碰 Pass 2/3。

**填写内容：**

- **一句话总览**：论文类型 + 核心发现，一句话。
- **5 Cs 快速评估**：
  - **Category**（类型）：RCT / 队列研究 / 病例对照 / 综述 / 基础研究 / ...
  - **Context**（上下文）：该领域当前共识，本文要解决什么问题
  - **Correctness**（合理性初判）：初步直觉，逻辑是否有明显漏洞
  - **Contributions**（贡献）：1-3 条
  - **Clarity**（清晰度）：写作质量，图表可读性
- **Figure 导读**（基于 fulltext.md 浏览各图 caption）：
  - 关键主图：列出并一句话概括每个主图要证明什么
  - 证据转折点：哪个 figure 是叙事的关键转折
  - 需要重点展开的 supplementary：如果有
  - 关键表格：列出

填完立即保存 formal note。

---

### Step 3: Pass 2 — 精读还原

填 `### Pass 2: 精读还原` 区域。**按 figure 顺序逐个处理。**

#### 图表类型定位（两步）

**Step A: 读 prepare 生成的 chart-type-map**
Step 1 的 `prepare` 输出中已包含 `chart_type_map` 路径。读该文件，获取每个 figure 的关键词命中结果。这只是建议。

**Step B: Agent 读 caption 做最终判断**

对每个 figure：
1. 读该 figure 的 caption（来自 prepare 返回的 `fulltext_md` 或 `figure_map`）
2. 根据 caption 内容，对照 [chart-reading/INDEX.md](chart-reading/INDEX.md) 判断图表类型
3. chart-type-map 建议和 Agent 判断不一致 → 以 Agent 判断为准
4. 无法确定类型 → 跳过 chart guide，按通用 figure 结构分析
5. 确定类型后，读对应的 chart-reading 指南（如 `chart-reading/条形图与误差棒.md`），按指南中的检查清单分析

#### 每张 Figure 的子标题（固定，不可少）

按以下格式填入 formal note 中该 figure 的 callout block：

```
**图像定位与核心问题**：页码 + 要回答什么问题
**方法与结果**：实验设计/数据来源/技术手段。核心数据、趋势、对比。
**图表质量审查**：按 chart-reading 指南检查坐标轴、单位、误差棒、统计标注等。
**作者解释**：作者在正文中对该图的解读
**我的理解**：自己的理解（区分于作者解释）
**疑点/局限**：读图时发现的疑问，用 `> [!warning]` 突出
```

#### 每张 Table 的子标题

```
回答什么问题、关键字段/分组、主要结果、我的理解、疑点/局限
```

#### 每张 figure 填完立即保存，再处理下一张。

#### 所有 figure/table 处理完后，填：

**关键方法补课**：简要解释不熟悉的实验技术（1-2 项即可）

**主要发现与新意**：
- 发现 1：...（来源：Figure X）
- 发现 2：...（来源：Figure Y / Table Z）

保存。

---

### Step 4: Postprocess（跑校验脚本，修正问题）

```bash
python scripts/ld_deep.py postprocess-pass2 <formal_note_path> --figures <N> --format text
```

- 输出 `OK` → 继续
- 输出错误 → 按错误提示修正（包含行号），修正后重新跑
- 最多 3 轮修正。3 轮后仍失败 → 报告剩余错误给用户

---

### Step 5: Pass 3 — 深度理解

填 `### Pass 3: 深度理解` 区域。基于 Pass 1/2 已写的内容。

**填写内容：**

- **假设挑战与隐藏缺陷**：隐含假设；如果放宽某个假设结论还成立吗；缺少哪些关键引用；实验/分析技术潜在问题
- **哪些结论扎实，哪些仍存疑**：
  - **较扎实**：...
  - **仍存疑**：...（用 `> [!warning]`）
- **Discussion 与 Conclusion 怎么读**：作者真正完成了什么；哪些地方有拔高；哪些是推测
- **对我的启发**：研究设计上；figure 组织上；方法组合上；未来工作想法
- **遗留问题**：...（用 `> [!question]`）

保存。

---

### Step 6: Final Validation

```bash
python scripts/ld_deep.py validate-note <formal_note_path> --fulltext <fulltext_path>
```

- 输出 `OK` → 告知用户精读完成
- 输出错误 → 修正缺失项，不报告成功直到通过

---

## Callout 格式规则

- `> [!important]`：每个 main finding
- `> [!warning]`：疑问、局限、证据边界、仍存疑条目
- `> [!question]`：遗留问题
- **间距：** 相邻 callout block 之间必须有空行，否则 Obsidian 会合并
  - 正确：`> [!important] A\n\n> [!important] B`
  - 错误：`> [!important] A\n> [!important] B`

## Supplementary 规则

- 默认不逐张展开 supplementary figure/table
- 仅在以下情况纳入：对主结论形成关键支撑、补足方法可信度、限制主文结论解释范围、作者在正文中明显依赖该补充材料
