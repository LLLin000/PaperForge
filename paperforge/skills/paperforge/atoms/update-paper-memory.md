# atom: update-paper-memory

维护单篇论文的 **Living Paper Memory Card（动态认知记忆卡片）**。存储于 SQLite (`paper_memory_cards` / `paper_memory_history`) 与工作区镜像 `<workspace>/ai/memory-card.json`，用于在多次跨会话讨论、精读与 PDF 批注间持续演化对论文的理解，而非堆积冗余对话记录。

---

## 核心原则

1. **Read-Before-Speak（先读后答，避免失忆与重复）**
   在回答或继续讨论之前，通过 `paper-context <KEY> --json` 查看 `data.living_memory.facets`（或直接运行 `paperforge memory-card get <KEY> --json`）。
   - 如果此前已沉淀了方法参数、硬伤或课题联想，应在当前讨论中**自然衔接并深化**，而不是重新泛泛概括。
   - **安全红线**：`living_memory` 反映历史认知沉淀；若被挑战或涉及精确数值，须对照原文/图表核实后修订（`refine`）。

2. **Refine-Don't-Append（提炼覆盖，而非无限追加聊天记录）**
   每次讨论有新收获时，将“原有该维度记忆 + 本次新验证洞见”**重写融合成一段紧凑的高信息密度摘要**（建议每维度 2–6 句话，上限 4000 字符），严禁把原始 Q&A 对话整段贴入。

---

## 标准认知维度（Facets）

| `facet` 标识符 | 显示标签 | 记录重点 |
|---|---|---|
| `idea_logic` | 研究思路与逻辑链 | 核心假说、论证骨架、关键实验跃迁与主要结论 |
| `methods_params` | 实验技术与关键参数 | 模型/样本量、刺激参数/剂量/时间窗、测量指标、关键对照与复现坑点 |
| `research_craft` | 研究技巧与巧思 | 实验设计巧妙之处、阴性/挽救对照思路、统计或图表呈现技巧 |
| `critique_limits` | 硬伤、边界与存疑 | 样本/机制边界、逻辑跳跃、未解决的问题与审稿级质疑点 |
| `my_connection` | 课题迁移与灵感 | 与用户当前研究课题、实验方案或潜在引用的具体关联 |

> [!note] 若上述 5 个标准维度确实无法覆盖特殊主题，可使用 2–32 位小写字母/数字/下划线自定义 `facet`（如 `biomarker_panel`），优先复用标准 5 维度以保持 Obsidian 面板整洁。

---

## 执行步骤

### 1. 读取现有记忆卡片

```bash
$PYTHON -m paperforge --vault "$VAULT" memory-card get <KEY> --json
```

若本会话此前已执行过 `paper-context <KEY> --json`，可直接复用其返回的 `data.living_memory`。

### 2. 融合更新有实质增量的维度

仅更新在本次交流/精读/PDF 批注中**产生了新洞见、新参数或纠正了旧认知**的维度：

```bash
$PYTHON -m paperforge --vault "$VAULT" memory-card refine <KEY> \
  --facet <idea_logic|methods_params|research_craft|critique_limits|my_connection> \
  --content "<融合旧认知与新发现的紧凑总结，关键数据标注 [p.X / Sec. Y / Fig. Z]>" \
  --json
```

### 3. 输出要求

- 每条 `refine` 必须保持事实依据可追溯（引用页码、章节或图表编号）。
- `memory-card refine` 会自动递增该维度的 `revision` 并在 `paper_memory_history` 保留版本快照，同时递增 `.state-seq.json` 触发 Obsidian Dashboard 与 Base 工作台实时刷新。
- 更新完成后，用 1–2 句简短向用户反馈本次更新了哪些记忆维度与版本号（如 `已深化「硬伤、边界与存疑 (r2)」`）。
