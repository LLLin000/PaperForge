# annotate-paper-pdf

> [!warning] Safety Rules
> - **严禁使用捏造的引文**：`--quote` 必须是 `fulltext.md` 或 OCR 文本中的**逐字原文片段**，不可自行改写后再传给定位引擎
> - **严禁同义复述型无效批注**：`--comment` 不得复述划线原句内容，必须写出推理角色、隐藏前提、参数坑点或跨章节联系
> - **永不修改原 PDF 字节**：所有 AI 批注写入侧车层（`<workspace>/annotations.jsonl` 与 SQLite `paper_annotations`，`author: "agent"`），Obsidian 内置阅读器通过 `[🤖 AI 批注层]` 独立开关呈现

受控的人机协同 PDF 精读批注工作流：结合 `paperforge` 3 级抗误差定位引擎，像导师/审稿人一样把关键批注直接打在 PDF 原页准确位置，并同步沉淀到论文的 Living Paper Memory Card。

---

## Pre-flight Checklist

- [ ] SKILL.md Section 1a Pre-flight 全部通过
- [ ] `$VAULT`、`$PYTHON` 已从 bootstrap 获取
- [ ] intent 已确定为 `annotate_paper_pdf`

---

## Step 1: 定位论文并检查原文与既有上下文

1. 若尚未掌握唯一 `<KEY>`，通过 planner 定位：
   ```bash
   $PYTHON -m paperforge --vault "$VAULT" query-plan "<identifier>" --intent locate --json
   ```
2. 获取论文完整上下文与章节树：
   ```bash
   $PYTHON -m paperforge --vault "$VAULT" paper-context <KEY> --structure --json
   ```
3. 核对前置状态：
   - 若 `data.paper.ocr_status != "done"` 或 `data.paper.has_pdf != true`：提示用户需要先完成 PDF 绑定与 OCR，停止批注。
   - 检查 `data.living_memory.facets`（已有长期认知）、`data.user_annotations`（用户自己已划的高亮和问题）以及 `data.paper.fulltext_path`。
4. 读取 `fulltext_path`（与 `structure.nodes`）通读全文骨架，定位关键段落、参数细节与核心图表。

---

## Step 2: 确定审阅视角（Review Lens）

根据用户指令选择一个 `--lens`（若用户只说“帮我批注这篇 PDF”，默认采用 `skeleton`）：

| `--lens` | 适用场景 | 批注焦点 |
|---|---|---|
| `skeleton` | 默认全篇领读 / 梳理逻辑 | 研究缺口 → 核心假说 → 关键转折实验 → 主结论推导链 |
| `methods` | 方法学迁移 / 实验复现 | 动物/细胞模型、样本量、频率/剂量/时间窗、对照设置、潜在复现坑点 |
| `critique` | 审稿挑刺 / 找硬伤与边界 | 统计效力不足、因果跳跃、混杂变量、阴性结果与结论外推风险 |
| `custom` | 用户指定特定问题 | 紧扣用户指定的目标问题逐处定位原文正反证据 |

> 每次批注控制在 **8–15 条高价值锚点**，覆盖全文关键节段与核心图表，避免铺满屏幕导致阅读疲劳。

---

## Step 3: 批量原子提交 AI 批注（强制优先，零引号转义问题）

**严禁调用面向用户的 `annotations add` 写入 AI 批注**。AI 批注必须经过 3 级 PDF 定位与后端护栏（OCR 就绪拦截、去重、防同义复述、15 条上限与 `batch_id` 追踪）：

1. **首选（MCP 工具）**：直接调用 **`paperforge_annotate_batch`**，传入 `paper_key`、`lens`、`replace_lens`（重跑同一视角时建议设 `true` 清旧留新）与结构化 `items` 数组。
2. **CLI 回退（一次事务提交整批，通过 stdin 传 JSON）**：
   ```bash
   cat << 'EOF' | $PYTHON -m paperforge --vault "$VAULT" annotations agent-apply <KEY> --input - --lens <skeleton|methods|critique|custom> --json
   {
     "lens": "skeleton",
     "replace_lens": false,
     "items": [
       {
         "quote": "<从 fulltext.md 原字复制的 1~2 句话>",
         "comment": "<导师/审稿人级洞见：论证角色、假设边界或跨章节关联>",
         "color": "purple"
       },
       {
         "figure_id": "figure_001",
         "comment": "<对这张图的核心机制读解或数据质疑>",
         "color": "blue"
       }
     ]
   }
   EOF
   ```
   （单条微调时仍可使用 `annotations agent-mark <KEY> ... --json`。）

> 提交后必须检查返回 JSON 中的 `created_count`、`skipped`（重复锚点）和 `rejected`（例如 `comment_paraphrases_quote` / `grounding_failed`），如有必要按原因修正引文或评论。

### 配色与分层约定

- **`purple`**：逻辑骨架 / 核心机制节点（`skeleton` 主色）
- **`blue`**：实验技术 / 关键参数 / 图表解读（`methods` 主色）
- **`red`**：硬伤 / 逻辑跳跃 / 存疑警告（`critique` 主色）
- **`green`**：关键定量结果 / 统计转折证据
- **`yellow`**：通用重点或用户定制检索命中（`custom`）

### 定位引擎行为说明（只读理解）

`annotations agent-mark` 内部自动执行 3 级抗误差定位：
1. **Stage 1**：基于 OCR block + ±1 页窗口锁定候选文字块；
2. **Stage 2a/2b**：折叠字符流归一化（自动跨越断行连字符、连字、LaTeX `$...$` 公式与希腊字母符号漂移，并在合并双栏 OCR 框时同页跨栏救援）计算精确词语框 → `exact_sentence` / `exact_cross_column`；
3. **Stage 3**：对纯扫描无文本层页面不乱画框，诚实降级为左侧页边竖线括号标记（`kind: "margin"`, `grounding_tier: "margin_fallback"`）。

---

## Step 4: 同步演进 Living Paper Memory Card

完成 PDF 批注后，按 `atoms/update-paper-memory.md` 将本轮批注提炼出的规律、参数、局限或启发融合写入 `memory-card refine`（对应 `idea_logic` / `methods_params` / `critique_limits` / `my_connection`）。

---

## Step 5: 汇报结果与 Obsidian 查看指引

向用户报告：
- 论文标题与所用 `--lens`；
- 成功写入的 AI 批注数量，以及定位质量分布（精确高亮 `exact_sentence` + 跨栏救援 `exact_cross_column` + 图表 `exact_object` + 扫描页边括号 `margin_fallback`）；
- 本次同步深化的 Living Paper Memory 维度；
- 提示用户直接在 Obsidian 点击「打开 PDF (`📄 PDF`)」即可看到实时刷新的批注，可通过顶部 **[🤖 AI 批注层]** 一键显隐、在侧边栏按 **[🤖 AI 领读]** 筛选，并对认同的条目点击 **[✓ 采纳]** 转为个人永久批注。
