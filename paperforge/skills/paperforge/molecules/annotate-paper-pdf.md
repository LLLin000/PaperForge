# annotate-paper-pdf

> [!warning] Safety Rules
> - **严禁使用捏造的引文**：`quote` 必须是 `paperforge_read_paper` 读出的原文（OCR `fulltext.md` 或 PDF 原生文本层）中的**逐字原文片段**，不可自行改写后再传给定位引擎
> - **严禁同义复述型无效批注**：`comment` 不得复述划线原句内容，必须写出推理角色、隐藏前提、参数坑点或跨章节联系
> - **永不修改原 PDF 字节**：所有 AI 批注写入侧车层（`<workspace>/annotations.jsonl` 与 SQLite `paper_annotations`，`author: "agent"`），Obsidian 内置阅读器通过 `[🤖 AI 批注层]` 独立开关呈现

受控的人机协同 PDF 精读批注工作流：直接通过 PaperForge MCP 工具读取全文（有 OCR 与无 OCR 原生 PDF 均可）并把关键批注原子打在 PDF 原页准确位置，再同步沉淀到论文的 Living Paper Memory Card。

---

## Pre-flight Checklist

- [ ] 已调用 `paperforge_brief(paper_key=...)` 且 `capabilities.safe_write == true`
- [ ] intent 已确定为 `annotate_paper_pdf`

---

## Step 1: 定位论文并读取原文与既有上下文（MCP-First）

1. 若尚未掌握唯一 `<KEY>`，调用 `paperforge_search` 或 `paperforge_library_query` 定位论文。
2. 调用 **`paperforge_paper_context`**（`key=<KEY>`, `structure=true`），获取：
   - `paper.has_pdf` / `paper.ocr_status`
   - `living_memory.facets`（已有长期认知）
   - `user_annotations`（用户自己已划的高亮和问题）
   - `structure`（若已完成 OCR 的章节树）
3. 核对前置状态：
   - 若 `paper.has_pdf != true`：提示用户需要先绑定 PDF，停止批注。
   - **无需等待 OCR**：无论是 OCR 已完成（`ocr_fulltext`）还是未跑 OCR 的原生 PDF（`native_pdf`），均直接调用 **`paperforge_read_paper`**（例如 `paper_key=<KEY>, pages="1-4"`，再按需翻页 `"5-8"`）通读逐字原文。若为纯扫描无文本层图像 PDF，可传 `page_hint` 生成页边括号批注，或提示用户按需调用 `paperforge_job(action="ocr", paper_keys=[KEY])`。

---

## Step 2: 确定审阅视角（Review Lens）

根据用户指令选择一个 `lens`（若用户只说“帮我批注这篇 PDF”，默认采用 `skeleton`）：

| `lens` | 适用场景 | 批注焦点 |
|---|---|---|
| `skeleton` | 默认全篇领读 / 梳理逻辑 | 研究缺口 → 核心假说 → 关键转折实验 → 主结论推导链 |
| `methods` | 方法学迁移 / 实验复现 | 动物/细胞模型、样本量、频率/剂量/时间窗、对照设置、潜在复现坑点 |
| `critique` | 审稿挑刺 / 找硬伤与边界 | 统计效力不足、因果跳跃、混杂变量、阴性结果与结论外推风险 |
| `custom` | 用户指定特定问题 | 紧扣用户指定的目标问题逐处定位原文正反证据 |

> 每次批注控制在 **8–15 条高价值锚点**，覆盖全文关键节段与核心图表，避免铺满屏幕导致阅读疲劳。

---

## Step 3: 批量原子提交 AI 批注

**首选直接调用 MCP 工具 `paperforge_annotate_batch`**（零引号转义、3 级 PDF 定位引擎、自动去重与防同义复述护栏、单批原子落盘）：

- 传入 `paper_key`、`lens`、`replace_lens`（重跑同一视角时建议设 `true` 清旧留新）与 `items`：
  - `quote`: 从 `paperforge_read_paper` 原字复制的 1–2 句话
  - `figure_id`: 图表编号（如 `"figure_001"` / `"table_001"`）
  - `comment`: 导师/审稿人级洞见（≥8 字，不得复述原句）
  - `color`: `purple`（逻辑骨架）/ `blue`（方法与图表）/ `red`（硬伤警示）/ `green`（定量证据）/ `yellow`（通用重点）
  - `page_hint`: 原文页码（可选，加速跨页消歧或用于纯扫描页）

管理/清理已有批注时直接调用 **`paperforge_annotations`**（`action`: `"list"` | `"adopt"` | `"clear_agent"` | `"delete"`）。

> **CLI 回退（仅限无 MCP 环境）**：在 Windows PowerShell 切勿直接在命令行参数拼接中文引号或 bash heredoc，请先将 JSON 写入临时文件并用 `--input <path>` 提交：
> `python -m paperforge --vault "<VAULT>" annotations agent-apply <KEY> --input payload.json --lens skeleton --json`

提交后必须检查返回结果中的 `created_count`、`skipped`（重复锚点）和 `rejected`（例如 `comment_paraphrases_quote` / `grounding_failed`），如有必要修正引文或评论后重提。

---

## Step 4: 同步演进 Living Paper Memory Card

完成 PDF 批注后，直接调用 **`paperforge_memory_refine`**（将旧记忆与本轮批注洞见融合为紧凑摘要写入 `idea_logic` / `methods_params` / `critique_limits` / `my_connection`）；若需沉淀可检索阅读摘录或工作记录，调用 **`paperforge_log_write`**。

> CLI 回退提示：在 Windows 下调用 `memory-card refine` 时同样优先用 `--input <file>`（传原始文本或 `{"facet": "...", "content": "..."}` JSON），避免 PowerShell 引号转义失败。

---

## Step 5: 汇报结果与 Obsidian 查看指引

向用户报告：
- 论文标题与所用 `lens`；
- 成功写入的 AI 批注数量，以及定位质量分布（精确高亮 `exact_sentence` + 跨栏救援 `exact_cross_column` + 图表 `exact_object` + 扫描页边括号 `margin_fallback`）；
- 本次同步深化的 Living Paper Memory 维度；
- 提示用户直接在 Obsidian 点击「打开 PDF (`📄 PDF`)」即可看到实时刷新的批注，可通过顶部 **[🤖 AI 批注层]** 一键显隐、在侧边栏按 **[🤖 AI 领读]** 筛选，并对认同的条目点击 **[✓ 采纳]** 转为个人永久批注。
