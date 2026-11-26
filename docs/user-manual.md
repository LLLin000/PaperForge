# PaperForge 使用手册

> 适用版本：`2.0.6+`（Obsidian Thin-Client + 原生 Rust 守护侧车 + 托管 Python 引擎）

---

## 一、PaperForge 是什么

PaperForge 将 Zotero 文献库与 Obsidian 工作区深度整合，采用**三层协同架构**，兼顾极速交互与可复现科研工作流：

1. **Obsidian 插件（Thin-Client）**：提供单一 `.base` 文献工作台、伴读 Companion 面板、内置无损 PDF 批注器、OCR 排错工作台、Quick Switcher 与四页极简设置中心。
2. **原生 Rust 守护进程（`paperforge-daemon`）**：驻留 `~/.paperforge/bin/`（`< 6–15 MB` 内存），承担零 Python 快路径（Base 快照、FTS5 搜索、Zotero 检测、配置校验）、`--mcp` 服务器（7 个原生工具）以及零前置运行时引导。
3. **托管 Python 核心（`paperforge`）**：通过 `uv` 自动部署到完全隔离的 `~/.paperforge/runtime/`，负责 Zotero 同步、云端/离线 V3 OCR 版面解析与图表裁切、SQLite + `sqlite-vec` 向量检索与 Living Memory Card 持久化。

---

## 二、安装与初始化（零 Python 前置、免 Better BibTeX）

### 2.1 前置条件

- **Obsidian 桌面版**（`minAppVersion: 1.11.4`）
- **Zotero 7 / 8**（直接只读读取 `zotero.sqlite`，**不再强制安装 Better BibTeX**）
- **无需预装 Python**：插件与 `paperforge-daemon` 自动拉取便携 `uv` 与托管 Python 3.12（如有本机 Python 3.11+ 亦可作为命令行宿主）
- **PaddleOCR API Token / Embedding API Key（可选）**：仅在开启云端 OCR 或语义检索时需要，所有密钥写入操作系统 Keyring（不存明文 `.env`）

### 2.2 一屏极速开启（Express Onboarding）

1. 在 Obsidian 社区插件市场、BRAT（`LLLin000/PaperForge`）或 [GitHub Releases](https://github.com/LLLin000/PaperForge/releases) 安装并启用 PaperForge。
2. 打开 **设置 → PaperForge**，即进入 **「一屏极速开启」**：
   - **第 1 步（一键启用引擎）**：自动下载校验 `paperforge-daemon` 与托管运行时（`~/.paperforge/runtime/`）。
   - **第 2 步（直连 Zotero 与目录组织预览）**：自动探测 `zotero.sqlite` 与文献集合；若检测到库根目录已有非空个人 `Literature` / `Resources` / `Bases` 文件夹，自动隔离到 `PaperForge/` 前缀下。支持实时预览 **选项 A（按 Zotero 顶级分类建子文件夹，推荐）** 与 **选项 B（全库平铺，依靠 Base 筛选条定位）**。
   - **第 3 步（可选 AI / 期刊指标配置）**：折叠区提供 PaddleOCR 与向量模型（硅基流动、百炼、智谱、OpenAI、Ollama 一键预设与实时测通）配置，留空即可先完成同步与批注。
3. 点击 **「保存配置并立即同步文献库」**，完成首次同步。

> 若需要纯终端/无头初始化，可执行：
> ```bash
> pip install "paperforge[vector]"
> paperforge setup --modular
> paperforge auth set ocr
> ```

### 2.3 设置中心四页架构与 10 态决策树

- **概览（Overview）**：顶部由 **10 态确定性决策树（Control Center）** 驱动，任何时刻仅呈现 1 张主卡片与 1 个最优先动作（如引擎热更新中、安全软件隔离提示、旧版 Vault `<3s` Fast Cutover 升级、连接 Zotero、同步受阻重试、一切就绪），下方为 5 行精简模块状态入口。
- **模块配置（Modules）**：分模块（基础环境、文献库、OCR、智能检索、Agent 集成）管理参数、运行探针与存储维护/回滚。
- **外观（Appearance）**：切换 **AsterLab 原色（默认）** 与 **跟随 Obsidian 主题**、排版密度，并按需开关液态玻璃模糊（默认关闭以零 GPU 占用运行）或减弱动画。
- **帮助（Help）**：查看版本更新说明、使用手册链接与 UI Gallery。

---

## 三、单一 `.base` 工作台与伴读 Companion

### 3.1 单一「文献库」Base 工作台（`Literature Hub.base`）

2.0.x 将旧版多面板 Base 收敛为 `Bases/` 下的单一 **「文献库」总表**：

- **持久化多维筛选条**：支持标题/作者/期刊即时过滤、专题与子分类级联筛选、处理状态胶囊与影响因子筛选。
- **高性能分块渲染与批量操作**：固定比例 `<colgroup>` 列宽 + 80 行分块流式渲染 + `content-visibility` 隔离；勾选左侧复选框（支持 `Shift` 连选）会在表头浮现上下文操作栏（批量解析全文、打开 PDF、诊断跳转）。
- **用户可编辑 frontmatter 字段**：`do_ocr`、`analyze`、`ocr_redo`、`tags`（`tags` 与用户自定义 YAML 键在 sync 时永久保留）。

### 3.2 伴读 Companion 面板（三态上下文）

通过左侧栏按钮或命令面板打开 **Companion 面板**，根据当前活动标签页自动切换：

- **Global 模式**：全库漏斗统计、系统健康状态与快捷入口（同步、体检、修复）；Companion 仅在真正打开时挂载事件监听并在关闭时完整清理。
- **Collection 模式**：展示当前专题的进度分布并限定范围操作。
- **Paper 模式**：
  - 展示 PDF / OCR / 精读状态指示器与快捷打开 PDF 按钮（内部机器 `fulltext.md` 已移出用户面板，仅在 OCR 排错工作台以只读脱敏预览方式查看）；
  - **Living Paper Memory Card**：展示并直接编辑 5 维认知卡片（`idea_logic`、`methods_params`、`research_craft`、`critique_limits`、`my_connection`）及查看/恢复修订历史；
  - **研究记录（Research Record）**：支持保存带引用原文、用途与 PDF 物理页码锚点的 JSONL 证据记录，支持精确字面检索与追加修正。

---

## 四、无损 PDF 批注阅读器（PaperForge PDF Annotator）

在 Base 表格或 Companion 点击 **打开 PDF**，即在 Obsidian 内打开原生 `loadPdfJs()` 渲染的阅读器：

- **双层 Apple Preview 风格工具条**：支持划词高亮 / 下划线 / 删除线、科研意图标签（`evidence`、`question`、`method`、`quote`）、区域框选截图（保存为工作区 `assets/<KEY>_ann_<id>.jpg`）、自由画笔、几何形状、文本框与便签。
- **零侵入侧车存储**：全部批注保存在 `<workspace>/annotations.jsonl` 并同步至 SQLite `paper_annotations` 表，**严格不修改原始 PDF 文件字节**，并记录 `pdf_sha256` 溯源校验（源文件变动时顶部提示 `Source PDF modified`）。
- **人机双层协作**：支持切换 `all / user / agent` 图层视图；AI 生成的批注支持一键 **采纳（Adopt）** 或 **晋升（Promote）** 为 `reading-log` 证据卡，并在执行 `/pf-deep` 时自动喂给 Agent 优先解答你的疑问。

---

## 五、OCR 解析与离线重建

1. 在 `.base` 工作台勾选论文点击 **解析全文**（或在笔记 frontmatter 设置 `do_ocr: true` 后运行 `paperforge ocr`）。
2. **输出位置**：
   - OCR 原始块与渲染产物保存在隐藏引擎目录 `.paperforge/ocr/<KEY>/`；
   - 裁切并合并好内嵌文字坐标的图表资产以 `<KEY>_figure_*.jpg` / `<KEY>_table_*.jpg` 独立命名写入论文工作区 `assets/`，由正式笔记原生嵌入渲染。
3. **零成本离线重建**：OCR 渲染/分块规则升级后，运行 `paperforge ocr rebuild`（或在 OCR 排错工作台触发）即可基于本地 `blocks.raw.jsonl` 零 API 费用重建图表与全文，并通过 `paperforge versions` 支持历史版本预览与安全切回。

---

## 六、记忆层与混合检索（SQLite + FTS5 + `sqlite-vec`）

PaperForge 2.0.x 已全面移除 ChromaDB 与本地 `sentence-transformers` 依赖，所有结构化索引、全文搜索与向量检索均统一收敛于单文件 `.paperforge/indexes/paperforge.db`：

### 6.1 结构化记忆与 FTS5（默认内置）

- 存储 `papers`、`assets`、`aliases`、`paper_annotations`、`paper_memory_cards`、`units` 与 FTS5 全文索引；
- 在 Zotero 未变动时，插件自动同步门禁通过 `stat()` 零开销跳过重复重建。

### 6.2 向量语义检索（可选，`sqlite-vec` `vec0`）

- 安装向量扩展依赖（插件托管环境默认包含，CLI 安装可使用 `pip install "paperforge[vector]"`）；
- 在设置「模块配置 → 智能检索」配置 API Key 与嵌入模型后点击构建，或运行：
  ```bash
  paperforge embed test-connection --json
  paperforge embed list-models --json
  paperforge embed build --resume --json
  ```
- 检索入口 `paperforge retrieve "<query>" --deep --json` 执行 BM25 + `vec_body` + `vec_objects` 全并集 RRF 融合排序；未构建向量时自动平滑回退到 FTS5 BM25。

---

## 七、与 AI Agent 协作（MCP Server + Skill Hub）

### 7.1 MCP 原生接入（推荐）

`paperforge-daemon --mcp --vault <VAULT_DIR>` 直接为 Claude Code、Cursor、Codex、OpenCode 等客户端提供 7 个受控工具（`paperforge_brief`、`paperforge_search`、`paperforge_library_query`、`paperforge_paper_context`、`paperforge_retrieve`、`paperforge_annotate_batch`、`paperforge_memory_refine`）：

```bash
paperforge-daemon agent-onboarding --vault <VAULT_DIR> --lang zh
paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
```

### 7.2 Skill 触发工作流与 Skill Hub

| 触发词 | 做什么 | 说明 |
| :--- | :--- | :--- |
| `/pf-deep <key>` | Keshav 三阶段组会式精读 | 结合 OCR 结构树与用户 PDF 疑问批注写入 `## 🔍 精读` 并执行 `paperforge deep-finalize <key>` |
| `/pf-paper <key>` | 交互式论文问答 | 不强制要求 OCR；结论可沉淀至 Living Memory Card |
| `/pf-status` / `/pf-sync` / `/pf-ocr` | 机械运维命令 | 走标准 JSON 契约，不人工 `grep` 猜测路径 |

运行 `paperforge-daemon skill-sync-all` 可将 `~/.paperforge/skills/paperforge/` 同步至所有已注册 Vault 与 Agent 工作区。

---

## 八、目录结构参考（`.paperforge/` 隐藏引擎布局）

```text
Vault/
├── .paperforge/                    ← 对 Obsidian 隐藏的引擎与派生索引目录
│   ├── ocr/<ZoteroKey>/            ← blocks.raw.jsonl、render/fulltext.md、图表裁剪源文件
│   ├── indexes/
│   │   ├── paperforge.db           ← SQLite SSOT（FTS5 + sqlite-vec vec0 + 批注 + 记忆）
│   │   ├── formal-library.json     ← 规范文献索引快照
│   │   └── .state-seq.json         ← 原子变更序号（驱动 Obsidian 实时刷新）
│   ├── backups/                    ← 升级/维护备份
│   └── exports/                    ← 可选：传统 Better BibTeX 导出目录
├── Resources/
│   └── Literature/                 ← 正式文献工作区（或按 domain 组织）
│       └── <domain>/<ZoteroKey> - <Title>/
│           ├── <ZoteroKey>.md      ← 主笔记（frontmatter + 精读内容 + 图表嵌入）
│           ├── annotations.jsonl   ← 无损 PDF 侧车批注
│           ├── assets/             ← <KEY>_figure_*.jpg / <KEY>_table_*.jpg / <KEY>_ann_*.jpg
│           └── ai/
│               ├── memory-card.json
│               └── discussion.md
├── Bases/
│   └── Literature Hub.base         ← 单一文献库总表视图
├── <平台相关>skills/paperforge/    ← Agent Skill 文件（由 Skill Hub 管理）
├── paperforge.json                 ← Vault 配置
└── .obsidian/plugins/paperforge/   ← Obsidian Thin-Client 插件
```

> 老版本 `System/PaperForge/` Vault 可在设置页决策树主卡一键升级，或执行 `paperforge upgrade --apply --fast-cutover --json` 在 3 秒内无损迁移至 `.paperforge/`。

---

## 协议与致谢

- 协议：[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)（仅限非商业使用）。
- 致谢：基于 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)、[Obsidian](https://obsidian.md)、[Zotero](https://www.zotero.org/) 与 [sqlite-vec](https://github.com/asg017/sqlite-vec) 等开源项目构建。
