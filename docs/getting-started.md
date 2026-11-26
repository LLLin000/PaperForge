# PaperForge 使用教程

> 面向终端用户。如果你刚安装完 PaperForge，从这里开始。

---

## 1. 一屏极速安装与连接 Zotero（`v2.0.6+`，零 Python 前置、无需 Better BibTeX）

> [!NOTE]
> 新手科研用户全程无需打开终端、无需提前安装 Python，也**不再强制安装 Better BibTeX 插件**：内置 Rust 守护进程（`paperforge-daemon`）会自动经由 `uv` 拉取完全隔离的托管运行时（`~/.paperforge/runtime/`），并以只读 SQLite Online Backup 快照直连 Zotero 的 `zotero.sqlite` 数据库读取文献、PDF 路径与分类树。

1. 在 Obsidian 社区插件市场（或 BRAT）安装并启用 **PaperForge** 后，打开「设置 → PaperForge」即进入 **「一屏极速开启」**：
   - **第 1 步（自动计算引擎）**：点击 **「一键启用引擎并同步文献库」**（或先部署引擎），后台静默安装隔离 Python 运行时并拉起 Rust 侧车。
   - **第 2 步（直连 Zotero 与目录隔离）**：插件自动定位 `Zotero/zotero.sqlite` 与文献分类。如果你的 Obsidian 库根目录下**已经存在非空个人 `Literature` / `Resources` / `Bases` 文件夹**，PaperForge 会自动识别并将自身目录隔离到 `PaperForge/Literature` 等路径，绝不与原有个人笔记混杂。
   - **实时选择 Domain 组织模式**：点击卡片即可在右侧实时预览 **选项 A（按 Zotero 顶级分类各自建子文件夹，推荐）** 或 **选项 B（全部文献平铺同目录，靠顶部胶囊在单一 Base 总表中筛选）**。
   - **第 3 步（可选 AI / 期刊分区增强）**：OCR 与 AI 语义检索（内置 `sqlite-vec` 向量索引与硅基流动、百炼、智谱、OpenAI、Ollama 一键预设与测通按钮；无需 ChromaDB）全部收在折叠区，留空也可先用基础文献管理与 PDF 批注。
2. 首次同步完成后，设置页顶部的 **10 态确定性决策树（Control Center）** 会自动转为「一切就绪」状态，老用户迁移旧版 Vault 也会在主卡片呈现 `<3s` 一键无损升级入口。

![一屏极速引导与 A/B 目录实时预览](images/ui-states/v4-13-express-onboarding-and-domain-preview.png)

> [!TIP]
> 隐藏引擎缓存、OCR 中间文件与内部 `fulltext.md` 默认收归 `.paperforge/`，避免拖慢 Obsidian 索引。若仍习惯使用传统 **Better BibTeX JSON** 工作流，可在设置「模块配置 → 文献库」中切换数据源模式。

---

## 2. 在四页设置中心管理模块与外观

`v2.0.5+` 将设置界面重构为四个清爽分页：

- **概览（Overview）**：顶部仅保留 1 张确定性决策树主卡与 1 个最优先主按钮，下方列出 5 行状态摘要入口（基础环境、文献库、OCR、智能检索、Agent 集成）。
- **模块配置（Modules）**：分模块配置 Zotero 路径、OCR API Key（写入 OS Keyring，不存明文 `.env`）、`sqlite-vec` 嵌入模型及存储维护/回滚。
- **外观（Appearance）**：在 **AsterLab 原色** 与 **跟随 Obsidian 主题** 间切换，调节信息密度，按需开启液态玻璃半透明或减弱动画。
- **帮助（Help）**：内置更新说明、文档入口与开发者 UI Gallery。

---

## 3. 在单一 `.base` 工作台高效筛选与同步

> 安装完成后，正式文献笔记保存在你的文献根目录（默认为 `Resources/Literature/<专题>/`；检测到同名用户目录时自动隔离为 `PaperForge/Resources/Literature/<专题>/`）。

![单一 Base 工作台与粘性多维筛选栏](images/ui-states/v4-01-base-workbench-all-states.png)

打开 `Bases/` 下的单一 **「文献库」总表**（`Literature Hub.base`），表头固定提供**持久化多维筛选条**（标题/作者/期刊过滤、专题与子分类筛选、状态胶囊），最左侧支持复选框与 `Shift` 连选并浮现批量操作栏。日常新增文献后只需点 **Sync Library**（或由后台 Zotero 文件变更门禁自动增量同步）即可秒级更新。

---

## 4. 触发 OCR

在 `.base` 工作台勾选论文点击批量 **解析全文**，或在正式笔记 frontmatter 里把 `do_ocr` 改为 `true` 后在 Dashboard / 命令面板执行 **Run OCR**（命令行：`paperforge ocr`）：

- OCR 中间产物保存在隐藏目录 `.paperforge/ocr/<key>/`，裁切好的图表以 `<key>_figure_*.jpg` / `<key>_table_*.jpg` 独立命名写入论文工作区 `assets/` 目录并在笔记中渲染；
- 内部机器 `fulltext.md` 收归 `.paperforge/ocr/<key>/render/fulltext.md`，不再冗余暴露到可见文献目录。

---

## 5. 阅读原版 PDF 并无损批注（Obsidian 内置阅读器）

在 `.base` 表格或 Companion 面板点击 **打开 PDF**，即可在 Obsidian 标签页使用内置 **PaperForge PDF Annotator**（基于原生 `loadPdfJs()`）：

- **双层标记工具条**：支持划词高亮 / 下划线 / 删除线（`evidence`、`question`、`method`、`quote`）、区域框选截图（自动生成 `assets/<key>_ann_<id>.jpg`）、自由画笔、几何图形、文本框与便签。
- **人机双层协作与原 PDF 零改动**：全部批注保存在 `<workspace>/annotations.jsonl` 并同步至 SQLite，严格不修改原始 PDF 字节；支持过滤 Human vs Agent 批注层、一键 `[✓ 采纳]` AI 批注或晋升为 `reading-log` 证据卡。

---

## 6. 深度精读（`/pf-deep`）

OCR 完成后，把笔记的 `analyze` 改为 `true`（可用 `paperforge deep-reading` 查看待精读队列），在 AI Agent 中输入 `/pf-deep <zotero_key>`：

- Agent 会综合 OCR 结构树、图表资产与你的 PDF 疑问批注执行 Keshav 三阶段精读，并调用 `paperforge deep-finalize <key>` 同步状态到 Dashboard。

---

## 7. 文献问答与 Living Memory（`/pf-paper`）

不强制要求 OCR 即可通过 `/pf-paper <zotero_key>` 进行交互式论文问答；问答或精读沉淀的 5 维认知卡片（`idea_logic`、`methods_params`、`research_craft`、`critique_limits`、`my_connection`）会同步展示在右侧 **Companion 面板**并保留修订历史。

---

## 8. 接入 AI Agent 与 MCP Server（Skill Hub）

`paperforge-daemon` 内置 **MCP（Model Context Protocol）服务端** 与跨平台 **Skill Hub**：

1. 在「设置 → 模块配置 → Agent 集成」点击一键配置（或在终端执行）：
   ```bash
   paperforge-daemon mcp-install --vault <VAULT_DIR> --platform claude
   paperforge-daemon mcp-check --vault <VAULT_DIR> --platform claude --probe-mcp
   ```
2. 支持 Claude Code、Cursor、Codex、OpenCode、Windsurf、GitHub Copilot、Cline 等平台；Agent 启动即可调用 `paperforge_brief`、`paperforge_search`、`paperforge_retrieve`、`paperforge_paper_context`、`paperforge_annotate_batch`、`paperforge_memory_refine` 等 7 个原生 MCP 工具。
3. 执行 `paperforge-daemon skill-sync-all` 可一键将 `~/.paperforge/skills/paperforge` 同步到所有已登记工作区。

---

## 9. 日常工作流与相关文档

```text
Zotero 添加文献（直接只读快照 zotero.sqlite，免 BBT 插件）
  -> 自动/手动 Sync
  -> 在单一 Base 总表筛选并打开内置 PDF 阅读器无损批注 (annotations.jsonl)
  -> 勾选并运行 OCR
  -> AI Agent (/pf-deep / /pf-paper / MCP) 精读与检索
```

- [完整使用手册](user-manual.md) — 全功能详尽指南
- [命令参考](COMMANDS.md) — Python CLI、Rust Daemon 与 MCP 工具速查
- [故障排除](troubleshooting.md) — 常见问题
- [更新指南](update-upgrade.md) — 如何升级 PaperForge
