# /LD-deep

基于单篇论文的组会式精读入口。

## 功能

1. 解析 `/LD-deep <query>` 中的查询词
2. 支持 Zotero key、标题片段、DOI、PMID、关键词
3. 优先搜索本地 Zotero 并锁定单篇论文
4. 绑定该论文对应的：
   - `<system_dir>/PaperForge/ocr/<KEY>/fulltext.md`
   - `<system_dir>/PaperForge/ocr/<KEY>/meta.json`
   - `<resources_dir>/<literature_dir>/.../KEY - Title.md`
5. 在正式文献卡片中检查或创建 `## 🔍 精读`
6. 以“研究思路 + figure-by-figure”方式一次性完成精读写回

## 执行原则

- `/LD-deep` 对用户来说是一次触发直接完成。
- 内部逻辑分两步：
  1. 先生成 `## 🔍 精读` 骨架和 figure 标题位
  2. 再补全所有空段
- **覆盖确认（强制）**：
  在启动精读前，主 agent **必须**读取 `{{FORMAL_NOTE}}`，检查是否已存在 `## 🔍 精读` 区域且包含非占位符的实质内容（如已填写的分析段落、非"（待补充）"的文本）。
  - 若检测到已有实质内容 → **必须**使用 Question tool 询问用户：
    - "追加"（保留现有内容，仅补充新增/空缺部分）
    - "覆盖"（删除现有精读，重新生成）
    - "跳过"（取消本次操作）
  - 用户选择"追加"时，subagent 应保留已有内容，仅填充空缺或补充新 section。
  - 用户选择"覆盖"时，subagent 应**先删除现有 `## 🔍 精读` 区域**（从 `## 🔍 精读` 到下一个同级或更高级 heading），再重新生成骨架并填写。
  - 用户选择"跳过"时，直接终止流程。
- 后续再次运行时（未询问用户或用户选择追加）：
  - 只补空段
  - 不覆盖已有内容
  - 不覆盖用户手改内容

## 精读定位

这不是综述提取，也不是信息摘录。
目标是模拟高水平博士/博士后组会讲解单篇论文的学习型精读。

主线必须是：

1. 文章整体研究思路
2. 主文 figure 逐张解析
3. 关键方法补课
4. 主要发现、新意、疑点与启发

## Supplementary 规则

- 默认不逐张展开 supplementary figure/table。
- 仅在以下情况下纳入：
  - 对主结论形成关键支撑
  - 补足方法可信度
  - 限制主文结论的解释范围
  - 作者在正文中明显依赖该补充材料

## 精读结构

骨架为纯文本 + 粗体标题，不使用 Obsidian callout 格式。采用 Keshav 三阶段阅读法组织：

```md
## 🔍 精读

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

## Figure 节要求

每个 figure 小节按以下顺序填写：

- **图像定位与核心问题**：页码 + 要回答什么问题
- **方法与结果**：方法 + 结果
- **作者解释**：作者对该图的解读
- **我的理解**：自己的理解（区分于作者解释）
- **在全文中的作用**：该图在整体故事线中的位置
- **疑点 / 局限**：读图时发现的疑问（可酌情用 `> [!warning]` 突出）

图像优先直接引用 `fulltext.md` 里已有的 OCR 图像链接。

## 使用示例

### 单篇精读（已知 key）

```bash
/LD-deep XGT9Z257
/LD-deep Predictive findings on magnetic resonance imaging
/LD-deep 10.1016/j.jse.2018.01.001
```

### 批量从待精读队列启动（/LD-deep queue）

```
/LD-deep queue
```

当不提供具体 key/标题时，agent 自动执行以下流程：

1. 运行 `python {{SCRIPT}} queue --vault {{VAULT}}`
2. 解析输出的 JSON 队列（`analyze=true` + `deep_reading_status != done` + `ocr_status`）
3. 按 OCR 状态分组展示：
   - **就绪**：OCR 已完成，可直接精读
   - **阻塞**：OCR 未完成，需先跑 `ocr` worker
4. 由用户选择篇目：
   - 若只有 1 篇就绪 → 直接执行单篇精读（等同于 `/LD-deep <key>`）
   - 若多篇 → 展示清单，用户选择后批量 spawn subagent 并行处理

**注意**：`queue` 模式只扫描 `library-records`（Base 控制记录），不扫描正式卡片。只有在 Base 里勾选 `analyze=true` 的论文才会进入队列。

## Subagent Spawn 指南（多篇并行时使用）

当需要并行处理多篇论文时，使用 Task tool 启动 subagent，每个 subagent 独立处理一篇。

### 变量替换

对每篇论文，替换以下四个变量：

| 变量              | 示例值                                                             |
| ----------------- | ----------------------------------------------------------------- |
| `{{ZOTERO_KEY}}`   | `Y5KQ4JQ7`                                                        |
| `{{FORMAL_NOTE}}`  | `<Vault>/<resources_dir>/<literature_dir>/骨科/Y5KQ4JQ7 - title.md` |
| `{{FULLTEXT_MD}}`  | `<Vault>/<system_dir>/PaperForge/ocr/Y5KQ4JQ7/fulltext.md` |
| `{{SCRIPT}}`      | `<Vault>/<skill_dir>/literature-qa/scripts/ld_deep.py` |

### Spawn 命令格式

```
Task(
  description="LD-deep {{ZOTERO_KEY}}",
  prompt="加载 subagent prompt: <Vault>/<skill_dir>/literature-qa/prompt_deep_subagent.md\n\n填入以下变量：\n- ZOTERO_KEY: {{ZOTERO_KEY}}\n- FORMAL_NOTE: {{FORMAL_NOTE}}\n- FULLTEXT_MD: {{FULLTEXT_MD}}\n- SCRIPT: {{SCRIPT}}",
  subagent_type="general"
)
```

### 多篇并行示例

假设要对 LMD5YVLP、NDPUMMCI、Y5KQ4JQ7、UBM39DTB 四篇并行精读：

1. 先行查询 formal-library.json 或检查文件系统，确认每篇的 FORMAL_NOTE 路径
2. 用 Bash tool 预跑 `python {{SCRIPT}} figure-index {{FULLTEXT_MD}}` 确认 OCR 存在
3. 四个 Task 并行启动，每篇独立
4. 等待所有 Task 完成，收集各篇的写入行数和验证结果

### 预检（必须）

在 spawn 之前，确认：
- `{{FULLTEXT_MD}}` 存在且非空（OCR 已完成）
- `{{FORMAL_NOTE}}` 所在目录存在（note 已被 selection-sync 创建）

如有任何一项不满足，subagent 应报错退出，不静默失败。
