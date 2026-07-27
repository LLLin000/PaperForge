# 功能说明

## Agent 如何利用 PaperForge 文献库

PaperForge 为 AI Agent 提供了强大的文献工作流基础：

1. **OCR 全文提取** — PaperForge 通过 OCR 将所有 PDF 文献转换成 Agent 能够轻松阅读的 Markdown 格式，这是文献工作流的基础。
2. **双层记忆检索** — 通过 sqlite-vec 结合的双层记忆层，Agent 既能通过文献元数据搜索精确定位文献，也能通过文献中的具体文本表述以及语义找到最匹配的文献。
3. **强大的学术支撑** — 在 OCR 与记忆层的基础上，一切工作都能让 Agent 通过 PaperForge Skill 快速找到文献支撑。你可以轻松地让 Agent 帮你完成有稳健文献支撑的综述写作、实验计划、灵感寻找、文献精读、某主题的精确总结……

---

## 文献库

同步 Zotero 文献库，构建可搜索的论文索引。文献库模块连接到你的 Zotero 数据目录，读取 BBT JSON 导出文件来建立正式文献索引。配置完成后，你可以从概览页和 OCR 工作区浏览、搜索和管理论文。

**前提：** 已安装 Zotero 桌面版和 Better BibTeX 插件，并将 BBT JSON 导出文件放置在保管库配置目录中。

---

## OCR 引擎

通过 OCR 从 PDF 中提取全文和图表。OCR 流水线对每篇论文执行多阶段处理：页面分析、图表检测、文本提取和结构角色分配。

从侧边栏图标或 `Ctrl+P → Open OCR Workspace` 打开 OCR 工作区。按状态筛选论文，使用搜索框定位特定论文，通过工具栏按钮批量处理。

**OCR 状态标签：** 已处理、需要更新、未处理、失败、待处理。

---

## 智能检索

PaperForge 的检索系统围绕三个检索意图组织：

- **Locate** — 定位已知论文（通过 DOI、key 或作者+年份）
- **Discover** — 发现一批相关论文
- **Content** — 查找论文中的事实、参数、方法或证据

**规划器**（`paperforge query-plan`）对问题分类并推荐最优命令：

- `paper-context` — 定位论文和章节导航
- `search` — 跨标题、摘要、作者的元数据搜索
- `retrieve` — 在 OCR 全文中检索正文证据

智能检索使用嵌入模型为论文全文构建向量索引。
向量可用时，`retrieve --deep` 在关键词匹配基础上增加语义搜索。
向量不可用时自动降级到元数据搜索。

**需要：** 兼容 OpenAI 的 API 端点和嵌入模型（用于向量功能）。
元数据搜索无需任何 API Key。
---

## Agent 集成

将 PaperForge Skills 部署到你偏好的 AI Agent 平台。Skills 让 Agent 可以直接从聊天界面访问论文搜索、OCR 状态和文献管理命令。

**支持的平台：** Claude Code、OpenCode 以及其他兼容 OpenMP 的 Agent。在设置中选择平台后，Skills 会自动部署。
