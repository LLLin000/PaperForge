# /pf-deep

## Purpose

基于单篇论文的组会式精读入口。

1. 解析 `/pf-deep <query>` 中的查询词
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
paperforge sync      # 生成 library-records 和正式笔记
paperforge ocr       # 完成 OCR 提取
paperforge deep-reading  # 查看精读队列状态
```

> `/pf-deep` 是 **Agent 层命令**，无直接 CLI 等效命令。其依赖的数据由上述 CLI 命令准备。

## Prerequisites

- [ ] library-record 已创建（`paperforge sync` 生成）
- [ ] `analyze: true` 已设置（在 library-record frontmatter 中）
- [ ] OCR 已完成（`ocr_status: done`）
- [ ] `fulltext.md` 存在且非空
- [ ] 正式笔记文件存在

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
/pf-deep XGT9Z257
/pf-deep Predictive findings on magnetic resonance imaging
/pf-deep 10.1016/j.jse.2018.01.001
```

### 批量从待精读队列启动

```bash
/pf-deep queue
```

当不提供具体 key/标题时，agent 自动执行以下流程：

1. 运行 `paperforge deep-reading` 查看精读队列（或 `python -m paperforge deep-reading --vault {{VAULT}}` 获取 JSON 格式队列）
2. 解析输出的队列状态（`analyze=true` + `deep_reading_status != done` + `ocr_status`）
3. 按 OCR 状态分组展示：
   - **就绪**：OCR 已完成，可直接精读
   - **阻塞**：OCR 未完成，需先跑 `paperforge ocr`
4. 由用户选择篇目：
   - 若只有 1 篇就绪 -> 直接执行单篇精读（等同于 `/pf-deep <key>`）
   - 若多篇 -> 展示清单，用户选择后批量 spawn subagent 并行处理

> **注意**：`queue` 模式只扫描 `library-records`（Base 控制记录），不扫描正式卡片。只有在 Base 里勾选 `analyze=true` 的论文才会进入队列。

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
- **处理**：Agent **必须**询问用户：
  - **"追加"** — 保留现有内容，仅补充新增/空缺部分
  - **"覆盖"** — 删除现有 `## 精读` 区域，重新生成
  - **"跳过"** — 取消本次操作
- **规则**：用户选择"追加"时保留已有内容；选择"覆盖"时先删除再重建；选择"跳过"时终止流程

### 未找到论文
- **表现**：Zotero key 无效或搜索无结果
- **解决**：确认 key 正确，或尝试用标题片段搜索

## Platform Notes

### OpenCode

- `/pf-deep` 在对话窗口直接输入
- Agent 使用 `paperforge paths --json` 获取 Vault 路径配置
- 多篇文章并行时使用 `Task` tool 启动 subagent，每篇独立处理
- 需要文件系统访问权限读取 OCR 结果和写入正式笔记

#### Subagent Spawn 指南（多篇并行时使用）

当需要并行处理多篇论文时，使用 Task tool 启动 subagent，每个 subagent 独立处理一篇。

**变量替换**：

| 变量 | 示例值 | 获取方式 |
|------|--------|---------|
| `{{ZOTERO_KEY}}` | `Y5KQ4JQ7` | 从 library-record 或 JSON 导出中获取 |
| `{{FORMAL_NOTE}}` | `<Vault>/<resources_dir>/<literature_dir>/骨科/Y5KQ4JQ7 - title.md` | 从 `paperforge paths --json` 或 library-record 中获取 |
| `{{FULLTEXT_MD}}` | `<Vault>/<system_dir>/PaperForge/ocr/Y5KQ4JQ7/fulltext.md` | 由 OCR worker 生成在 ocr 目录下 |
| `{{SCRIPT}}` | `<Vault>/<skill_dir>/literature-qa/scripts/ld_deep.py` | 从 `paperforge paths --json` 获取 `ld_deep_script` 字段 |

**Spawn 命令格式**：

获取路径信息：
```bash
paperforge paths --json
# 返回 JSON，包含 worker_script, ld_deep_script, skill_dir 等字段
```

然后使用以下格式启动 subagent：
```
Task(
  description="pf-deep {{ZOTERO_KEY}}",
  prompt="加载 subagent prompt: <Vault>/<skill_dir>/literature-qa/prompt_deep_subagent.md\n\n填入以下变量：\n- ZOTERO_KEY: {{ZOTERO_KEY}}\n- FORMAL_NOTE: {{FORMAL_NOTE}}\n- FULLTEXT_MD: {{FULLTEXT_MD}}\n- SCRIPT: {{SCRIPT}}",
  subagent_type="general"
)
```

**多篇并行示例**：

假设要对 LMD5YVLP、NDPUMMCI、Y5KQ4JQ7、UBM39DTB 四篇并行精读：

1. 先行查询 formal-library.json 或检查文件系统，确认每篇的 FORMAL_NOTE 路径
2. 用 Bash tool 预跑 `python {{SCRIPT}} figure-index {{FULLTEXT_MD}}` 确认 OCR 存在
3. 四个 Task 并行启动，每篇独立
4. 等待所有 Task 完成，收集各篇的写入行数和验证结果

**预检（必须）**：

在 spawn 之前，确认：
- `{{FULLTEXT_MD}}` 存在且非空（OCR 已完成）
- `{{FORMAL_NOTE}}` 所在目录存在（note 已被 selection-sync 创建）

如有任何一项不满足，subagent 应报错退出，不静默失败。

### Codex

> **Future**：计划支持。预计通过 API 调用实现类似功能。

### Claude Code

> **Future**：计划支持。预计通过工具调用或文件附件实现。

## 精读结构参考

### 执行原则

- `/pf-deep` 对用户来说是一次触发直接完成。
- 内部逻辑分两步：
  1. 先生成 `## 精读` 骨架和 figure 标题位
  2. 再补全所有空段
- 后续再次运行时（未询问用户或用户选择追加）：
  - 只补空段
  - 不覆盖已有内容
  - 不覆盖用户手改内容

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

**证据边界**：区分三层信息：`论文结果`、`作者解释`、`我的理解/推断`。不要把样本内观察直接写成普遍规律，不要把相关性写成因果，不要把未进入最终模型的指标写成已被稳定验证的联合诊断结论。

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
- **疑点 / 局限**：读图时发现的疑问（可酌情用 `> [!warning]` 突出）

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

图像优先直接引用 `fulltext.md` 里已有的 OCR 图像链接。

## See Also

- [pf-paper](pf-paper.md) — 快速摘要与问答
- [AGENTS.md](../AGENTS.md) — 完整使用指南、架构说明、常见问题
- [docs/COMMANDS.md](../docs/COMMANDS.md) — 命令总览与矩阵
