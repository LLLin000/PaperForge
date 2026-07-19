# PaperForge 使用手册

> 版本：1.5.15+

---

## 一、PaperForge 是什么

PaperForge 是一个 Obsidian 插件，把你 Vault 变成文献研究中心。它可以：

1. 从 Zotero 自动同步文献目录，为每篇论文生成规范的 Obsidian 笔记
2. 把 PDF 上传到 PaddleOCR，提取全文 Markdown 和图片
3. 在 Dashboard 中查看全文、跟踪论文处理状态、重做 OCR
4. 与 AI Agent（OpenCode / Claude Code / Cursor 等）协作，进行深度阅读、文献搜索、方法论提取
5. 基于全文建立记忆层（FTS 全文搜索 + 向量语义搜索 + 结构化索引）

---

## 二、安装与初始化

### 2.1 前置条件

你需要先确保系统中有以下工具：

- **Zotero 7**（文献管理软件）
- **Better BibTeX 插件**（Zotero 的导出插件）
- **Python 3.10+**
- **PaddleOCR API Token**（百度飞桨 OCR 服务）

### 2.2 安装 Guide

1. 下载 PaperForge 插件，将 `main.js`、`manifest.json`、`styles.css` 放入 Vault 的 `.obsidian/plugins/paperforge/` 目录
2. 在 Obsidian 的 Community Plugins 中搜索并启用 PaperForge
3. 打开 PaperForge 设置：

在 Obsidian 左侧 Ribbon 点击 PaperForge 图标，或使用命令面板搜索 `PaperForge: Dashboard`。

#### 步骤 1：安装标签页中配置

打开设置后默认在「安装」标签页。你会看到：

- **Runtime 状态**：显示插件版本和 Python 包的版本是否匹配
- **Python 解释器**：系统会自动检测。你也可以手动指定路径（如 `C:\Python310\python.exe`）
- **PaddleOCR API Key**：填写你从百度飞桨申请的 API Token
- **安装向导**：首次安装点击 `开始安装`，会自动检测环境并引导你完成配置

安装向导会自动帮你：

- 在 Vault 中创建 PaperForge 目录结构（`System/PaperForge/`、`Resources/Literature/`、`Bases/` 等）
- 检测 Python 环境
- 检测 Zotero 和 Better BibTeX
- 配置 Zotero 数据目录
- 选择你的 AI Agent 平台（OpenCode / Claude Code / Cursor 等）
- **部署 Agent Skill 文件**：向导会根据你选择的平台，自动将 PaperForge Skill 部署到对应的 Vault 目录

#### 步骤 2：Skills 查看

在「功能」标签页的 Skills 区域，你可以看到哪些 Skill 已经部署到你的 Vault 中。每个 Skill 对应一个 SKILL.md 文件。你可以在这里关闭你不希望 Agent 使用的 Skill。这一页只是查看和管理，实际部署是在安装向导中完成的。

### 2.3 配置 Better BibTeX 自动导出

在 Zotero 中安装 Better BibTeX 后，你需要为每个领域配置一个自动导出。

**核心概念**：一个 Zotero Collection（子分类文件夹）对应一个 Base 视图文件。比如你在 Zotero 中有一个名为"骨科"的子分类文件夹，导出这个 Collection 后，Obsidian 中会自动生成 `骨科.base`。这个 Base 文件包含的就是该 Collection 下所有子文件夹里的论文，并且会随 Zotero 的修改实时同步。

**具体操作**：

1. 在 Zotero 左侧面板，右键点击你想导出的 Collection（如"骨科"）
2. 选择 `导出 Collection...`（Export Collection...）
3. 格式选择：**Better BibTeX JSON**（这是唯一支持的格式）
4. 勾选 `保持自动更新`（Keep updated）
5. 导出路径：选择 Vault 中的 `System/PaperForge/exports/`

**实际效果**：
- 导出的 JSON 文件名自动使用 Collection 名称
- Obsidian 的 `Bases/` 目录下会自动生成同名的 `.base` 文件
- Base 文件中的论文列表是该 Collection 下所有子文件夹中的文献
- 一次配置，永久自动同步：每次 Zotero 中新增/删除/修改文献，JSON 和 Base 都会刷新

**不需要每加一篇论文就导一次**：自动导出会持续保持同步。

### 2.4 第一次 Sync

打开 Dashboard，点击左侧的 `Sync Library` 按钮。

Sync 做了什么：

1. 读取 `System/PaperForge/exports/` 下的 JSON 导出文件
2. 为每篇论文生成 Obsidian 笔记（`Resources/Literature/<domain>/<key> - Title/<key>.md`）
3. 建立文献索引（`System/PaperForge/indexes/formal-library.json`）
4. 重建 FTS 记忆数据库

---

## 三、Dashboard 完全指南

Dashboard 是 PaperForge 的核心界面。它有 **三种模式**，根据你当前在 Obsidian 中打开的文件自动切换。

### 3.1 全局模式（Global Mode）

当你没有打开任何特定论文时，Dashboard 显示全局面板。

**Library Snapshot**：显示你的文献库总览

- `papers`：总论文数
- `PDFs ready`：有 PDF 的论文数
- `OCR done`：已完成 OCR 的论文数
- `deep-read done`：已完成深度阅读的论文数

**System Status**：系统健康状态指示灯

| 组件 | 含义 |
|------|------|
| Runtime | 插件版本和 Python CLI 版本是否匹配 |
| Index | 文献索引是否存在且有效 |
| Zotero Export | 是否有 Zotero 导出文件 |
| OCR Token | PaddleOCR API Key 是否已配置 |
| Memory Layer | 记忆层（FTS + 索引）是否健康 |

**需要处理**：如果有任何状态异常，Dashboard 会列出问题并提供 `Run Doctor` 和 `Repair Issues` 按钮。

**Start Working**：提供快捷操作按钮

- `Sync Library`：同步 Zotero → PaperForge
- `Run OCR`：开始 OCR 队列处理
- `Redo OCR`：执行一次重做 OCR
- `Run Doctor`：运行诊断
- `Repair Issues`：修复状态不一致

### 3.2 论文模式（Paper Mode）

当你打开一篇论文的工作区笔记（`<key>.md`）或 PDF 时，Dashboard 自动切换到此模式。

**论文元数据**：标题、作者、年份

**状态条**：三个圆形指示器

| 指示器 | 含义 | 状态 |
|--------|------|------|
| PDF | 论文是否有 PDF | ✓（有） / ○（无） |
| OCR | OCR 处理状态 | ✓ done / ○ pending / ✗ failed |
| 精读 | 深度阅读是否完成 | ✓ done / ○ pending |

**快捷按钮**

| 按钮 | 功能 |
|------|------|
| 打开 PDF | 在 Obsidian 中打开 PDF |
| 打开全文 | 打开 OCR 提取的全文 Markdown |

**文章概览（Paper Overview）**：从笔记的 `## 精读` 区域中自动提取摘要。如果还没有精读，显示提示信息。

**下一步推荐（Next Step）**：根据当前论文的处理状态，智能推荐下一步操作：

- `Sync Needed`：论文尚未同步 → 点击 Sync
- `OCR Needed`：PDF 已就绪，全文未提取 → 点击 OCR
- `Ready for Deep Reading`：全文就绪 → 复制 `/pf-deep <key>` 命令到 Agent
- `All Set`：所有流程完成

**最近讨论**：显示 `ai/discussion.md` 中最新的问答记录。

**技术详情**（折叠区）：显示更多内部状态和两个重要的勾选框：

- `do_ocr`：将此论文加入 OCR 队列
- `analyze`：标记此论文需要深度阅读
- `Fulltext Path`：OCR 全文本的完整 Vault 路径

### 3.3 领域模式（Collection Mode）

当你打开某个领域的 `.base` 文件时，Dashboard 切换到此模式。

**Workflow Overview**：该领域的漏斗图，显示 Total → PDF Ready → OCR Done → Deep Read 的数量。

**OCR Pipeline**：彩色进度条，一眼看清该领域 OCR 的 `Pending / Processing / Done / Attention` 分布。

**快捷操作**：`Run OCR`、`Sync Library`、`Redo OCR`（仅影响该领域的论文）。

---

## 四、Base 视图完全指南

每个领域都有对应的 Base 文件（`Bases/<domain>.base`）。Base 是 Obsidian 的数据库视图，可以像表格一样浏览、排序、筛选文献。

### 4.1 四个标准面板

| 面板 | 筛选条件 | 用途 |
|------|---------|------|
| **控制面板** | 无筛选 | 显示该领域全部论文的完整信息。包括 `has_pdf`、`do_ocr`、`analyze`、`ocr_status`、`deep_reading_status` 等所有 workflow 列 |
| **待 OCR** | `do_ocr == true && ocr_status == "pending"` | 列出需要 OCR 处理的论文。勾选这里的 `do_ocr`，下次 Run OCR 就会处理 |
| **待深度阅读** | `analyze == true && ocr_status == "done" && deep_reading_status == "pending"` | 列出 OCR 已完成但未精读的论文 |
| **Redo OCR** | `ocr_status == "done"` | 列出所有 OCR 已完成的论文。勾选 `ocr_redo`，点 Redo 按钮即可重新提取全文 |

### 4.2 各列的含义

| 列名 | 含义 | 谁控制 |
|------|------|--------|
| `title` | 论文标题 | Zotero 自动 |
| `year` | 发表年份 | Zotero 自动 |
| `first_author` | 第一作者 | Zotero 自动 |
| `journal` | 期刊名 | Zotero 自动 |
| `impact_factor` | 影响因子 | 自动推算 |
| `has_pdf` | 是否有 PDF | 自动检测 Zotero 附件 |
| `do_ocr` | 是否提交 OCR | **用户可修改**（勾选 = 下次 Run OCR 时会处理这篇） |
| `analyze` | 是否标记精读 | **用户可修改**（勾选 = 准备好让 Agent 精读这篇） |
| `ocr_status` | OCR 处理状态 | 系统自动：`pending` → `processing` → `done` / `failed` |
| `deep_reading_status` | 深度阅读状态 | 系统自动：`pending` → `done` |
| `ocr_redo` | 是否标记重做 | **用户可修改**（勾选 = 下次 Redo OCR 时处理这篇） |
| `ocr_time` | OCR 完成时间 | 系统自动 |
| `pdf_path` | PDF 链接 | 系统自动 |
| `fulltext_md_path` | 全文路径 | 系统自动 |
| `collection_path` | Zotero 中的 Collection 路径 | Zotero 自动 |
| `collection_tags` | Collection 标签 | Zotero 自动 |

### 4.3 用户可手动修改的字段

在整个 frontmatter 中，**以下字段是用户可以手动修改的**，其余全部由系统自动维护：

- `do_ocr`：勾选后，论文进入 OCR 队列
- `analyze`：勾选后，论文标记为"待深度阅读"
- `ocr_redo`：勾选后，论文标记为"需要重做 OCR"
- `tags`：标签列表，系统默认写入 `文献阅读` 和领域名，你可以随意增删，系统不会覆盖你的修改

> **警告**：不要手动改 `ocr_status`、`deep_reading_status`、`fulltext_md_path`、`pdf_path` 等系统字段。这些会被 sync 覆盖。

### 4.4 `tags` 和 `collection_path` 的来源

- `tags`：从 Zotero 的标签同步，同时系统默认写入 `文献阅读` 和领域名。**你可以在 Obsidian 中增删 tags，系统不会覆盖你加的 tag**
- `collection_path`：来自 Zotero 的 Collection 层级。例如 Zotero 中 `骨科 → 软骨修复 → 生物反应器` 的文章，其 `collection_path` 就是 `骨科|软骨修复|生物反应器`
- `collection_tags`：Collection 路径中每一级作为标签存入

---

## 五、完整工作流

### 5.1 新增论文的标准流程

```
Zotero 添加文献 → 自动导出 JSON → Sync → 勾选 do_ocr → Run OCR → 打开全文 → Agent 精读
```

1. **在 Zotero 中添加文献**：通过 DOI、PMID 或网页抓取
2. **Better BibTeX 自动导出**：JSON 文件自动更新（因为你已经配置了自动导出）
3. **Dashboard → Sync**：读取最新的 JSON 导出，生成/更新 Obsidian 笔记
4. **勾选 do_ocr**：在 Base 的「待 OCR」面板中勾选 `do_ocr`，或者直接在论文笔记的 frontmatter 中手动设为 `true`
5. **Dashboard → Run OCR**：提交 OCR 任务，等待完成
6. **打开全文**：OCR 完成后，Dashboard 显示 `打开全文` 按钮
7. **Agent 精读**：在 Agent 中调用 PaperForge Skill，让 Agent 读取全文

### 5.2 重建全文（Redo OCR）的标准流程

当你需要重新提取某篇论文的全文时：

1. 在 Base 的「Redo OCR」面板中找到目标论文
2. 勾选 `ocr_redo`
3. 在 Dashboard 或 Ribbon 点击 `Redo OCR`
4. 系统自动：
   - 删除旧的 OCR 产物
   - 删除工作区旧 `fulltext.md`
   - 强制 `do_ocr: true`
   - 立即重跑 OCR
   - 成功后写回 `ocr_redo: false`

**注意**：如果 OCR 失败，`ocr_redo` 会保持 `true`，方便你再次尝试。

### 5.3 搜索与查找论文

有三种搜索方式，覆盖面不同：

| 方式 | 搜索范围 | 在哪里用 |
|------|---------|---------|
| Base 面板的搜索框 | 标题、作者 | Obsidian 中直接搜 |
| 调用 PaperForge Skill | 标题、摘要、作者、全文 | Agent 中调用 |
| `paperforge search` CLI | 标题、摘要、作者、期刊 | 命令行 |

---

## 六、记忆层（Memory Layer）

记忆层是 PaperForge 的"大脑"，由两部分组成：

### 6.1 结构化记忆（Memory DB）

- 基于 **SQLite + FTS5**（全文搜索引擎）
- 存储每篇论文的元数据（标题、作者、摘要、期刊、领域、Collection 等）
- 支持精确的字段查询（按作者、年份、领域、OCR 状态等）
- 每次 `Sync` 后自动重建

### 6.2 向量语义搜索（Vector DB）【可选功能】

> 向量数据库是**可选择性开启**的。即使没有开启，Agent 仍然可以使用 FTS 元数据搜索来查找论文。

- 基于 **ChromaDB**（向量数据库）
- 将所有已完成 OCR 的论文全文切分成段落，生成向量
- 支持**语义搜索**：即使用自然语言描述一个概念（如 "75 Hz 电刺激对软骨细胞的分化影�"），ChromaDB 也能在正文中找到匹配的段落
- 这是检索论文最强大的方式——它搜索的不只是标题和摘要，而是正文的所有内容

**开启方式**：

1. 在插件设置页的「功能」标签页中，找到"向量数据库"区域
2. 勾选开启，可选配置 embedding 模型（如 OpenAI embedding API、本地 sentence-transformers 等）
3. 点击"构建向量数据库"
4. 构建完成后，Agent 就可以使用语义搜索在正文 Methods/Results 中匹配概念

---

## 七、与 Agent 协作

### 7.1 PaperForge Skill 是什么

PaperForge Skill 是部署到 Vault 中的 Agent 技能文件（`SKILL.md`）。它做的事情是：

1. **让 Agent 知道你的文献库存在**：Agent 会通过 bootstrap 脚本获取 Vault 路径、Python 位置、文献目录
2. **给 Agent 提供搜索工具**：Agent 会使用 `paperforge search`（元数据搜索）和 `paperforge retrieve`（语义搜索）来查找论文
3. **规范 Agent 的文献操作行为**：Agent 不会用 `grep` 乱搜文件、不会自己拼路径、不会只看摘要就回答事实性问题
4. **定义 Agent 的研究工作流**：精读论文、搜索文献、文献问答、记录问答、提取方法论等

### 7.2 Agent 读了这个 Skill 会做什么

当 Agent 加载 PaperForge Skill 后，它会：

1. 执行 `pf_bootstrap.py` 获取路径和配置
2. 执行 `agent-context` 获取文献库概览
3. 检查 `runtime-health` 确认系统健康
4. 根据你的输入判断意图（搜文献、读论文、找证据、保存笔记、提取方法论）
5. 路由到对应的 workflow 执行

### 7.3 所有 Agent 能力详解

当你安装了 PaperForge Skill 后，Agent 可以直接响应如下自然语言意图：

| 你说什么 | Agent 会做什么 |
|---------|---------------|
| "找文献"、"搜文献"、"找一下"、"搜一下" | 搜索论文目录，返回候选列表 |
| "库里有什么"、"collection 里" | 列举领域/Collection 中的论文 |
| "读一下这篇"、"看看这篇"、"这篇论文" | 打开指定论文进行阅读 |
| "找证据"、"找支持"、"找依据"、"找参数" | 检索全文中的具体证据和方法 |
| "精读"、"/pf-deep" | 三阶段深度阅读 |
| "记一下"、"保存这次"、"记录一下" | 保存当前会话的阅读笔记 |
| "提取方法论" | 从论文中提取可复用的研究方法卡片 |
| "/pf-paper <key/DOI>" | 快速定位并阅读已知论文 |

### 7.4 如果 Agent 没有自动读取 Skill 怎么办

- **通用方法**：在对话中直接写 `调用 paperforge skill`，或告诉 Agent "读取 vault 中 .opencode/skills/paperforge/SKILL.md"（路径根据你的平台调整）
- 如果 Agent 仍然无法加载，检查 Vault 的对应 skills 文件夹（如 `.opencode/skills/`）下是否存在 `paperforge/` 目录
- 如果不存在，在插件设置页重新运行一次安装向导，或者手动将 Skill 文件复制进去
- 重启你的 CLI / Agent 客户端后重试

**确认 Agent 已加载 Skill 的标志**：Agent 会先运行 `pf_bootstrap.py` 并输出路径变量，而不是直接用 `grep` 搜文件。

### 7.5 Agent 使用的搜索工具

Agent 有三种搜索武器，不会只用一种：

| 工具 | 命令 | 搜索范围 |
|------|------|---------|
| 元数据搜索 | `paperforge search "query"` | 标题、摘要、作者、期刊、领域、Collection 路径 |
| 语义全文搜索 | `paperforge retrieve "query"` | OCR 正文全部内容（需开启向量 DB） |
| Collection/领域列举 | `paperforge context --collection/--domain` | 指定 Collection 下的完整论文列表 |

**Agent 禁止手动 `grep` / `rg` / `glob` 搜文件**。这是 Skill 的硬性规则。如果 Agent 试图这样做，说明它没有正确加载 Skill，你需要提醒它。

### 7.6 Agent 的意图路由顺序

Agent 按以下优先级判断你要做什么：

1. 机械命令（`/pf-sync`、`/pf-ocr`、`/pf-status`） → 直接执行
2. 命令别名（`/pf-deep` → 深度分析，`/pf-paper` → 快速阅读）
3. 你要保存/归档 → 执行 capture
4. 你给定了明确论文 → 执行阅读
5. 你要找论文列表 → 执行检索
6. 你要找具体证据 → 执行证据查找
7. 意图不清 → Agent 会问你两个问题澄清

---

## 八、目录结构参考

```
Vault/
├── System/
│   └── PaperForge/
│       ├── ocr/<ZoteroKey>/        ← OCR 产物
│       │   ├── fulltext.md         ← 唯一的正文真相源
│       │   ├── json/result.json    ← OCR 原始结果
│       │   ├── images/             ← 提取的图片
│       │   ├── pages/              ← 页缓存
│       │   └── meta.json           ← OCR 进度
│       ├── exports/                ← Better BibTeX JSON 导出文件
│       └── indexes/                ← 文献索引
│           └── formal-library.json
├── Resources/
│   └── Literature/                 ← 论文工作区
│       └── <domain>/<ZoteroKey> - <Title>/
│           ├── <ZoteroKey>.md      ← 主笔记（frontmatter + 精读内容）
│           └── ai/                 ← AI 产物
│               └── discussion.md   ← Agent 对话记录
├── Bases/                          ← Obsidian Base 视图
│   └── <domain>.base
├── <平台相关>skills/paperforge/    ← Agent Skill 文件
│   └── SKILL.md
└── .obsidian/plugins/paperforge/   ← 插件本体
```
