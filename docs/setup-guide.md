# PaperForge 安装配置与使用指南

> 本文档面向**首次使用 PaperForge 的新用户**，从零开始覆盖安装、配置、使用全流程。

---

## 目录

1. [前置条件](#1-前置条件)
2. [安装 PaperForge](#2-安装-paperforge)
3. [运行安装向导](#3-运行安装向导)
4. [配置 Zotero 和 Better BibTeX](#4-配置-zotero-和-better-bibtex)
5. [验证安装](#5-验证安装)
6. [首次使用流程](#6-首次使用流程)
7. [日常使用命令](#7-日常使用命令)
8. [更新 PaperForge](#8-更新-paperforge)
9. [故障排除](#9-故障排除)

---

## 1. 前置条件

### 1.1 需要安装的软件

| 软件 | 版本要求 | 用途 | 下载地址 |
|------|---------|------|---------|
| Python | 3.10+ | 运行 PaperForge | https://python.org/downloads/ |
| Zotero | 最新版 | 文献管理 | https://zotero.org/download/ |
| Better BibTeX | 最新版 | Zotero 插件 | https://retorque.re/zotero-better-bibtex/installation/ |
| Obsidian | 最新版 | 笔记软件 | https://obsidian.md/download/ |
| Git | 可选 | 手动更新 | https://git-scm.com/downloads/win |

### 1.2 需要申请的 API Key

- **PaddleOCR API Key**：用于 PDF 自动 OCR 提取
  - 访问 https://paddleocr.baidu.com
  - 注册账号 → 创建应用 → 获取 API Token
  - 免费额度通常足够个人使用

### 1.3 确认 Zotero 已有文献

在开始安装前，确保：
1. Zotero 已安装并打开过至少一次
2. Zotero 中已有至少一篇带 PDF 附件的文献
3. Better BibTeX 插件已安装（Zotero → 工具 → 插件 → 搜索 Better BibTeX）

---

## 2. 安装 PaperForge

### 方式 A：pip 安装（推荐）

打开 PowerShell（Windows）或终端（macOS/Linux）：

```powershell
pip install git+https://github.com/LLLin000/PaperForge.git
```

验证安装：
```powershell
paperforge --help
```

如果看到命令列表，说明安装成功。

### 方式 B：一键安装脚本（Windows 新用户）

如果不太熟悉命令行，使用一键脚本：

```powershell
powershell -c "iwr -Uri https://raw.githubusercontent.com/LLLin000/PaperForge/master/scripts/install-paperforge.ps1 -OutFile install.ps1; ./install.ps1"
```

脚本会自动检查 Python、安装 PaperForge，然后提示运行 `paperforge setup`。

### 方式 C：从源码安装（开发者用）

```powershell
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge
pip install -e .
```

---

## 3. 运行安装向导

### 3.1 启动向导

```powershell
paperforge setup
```

你会看到一个图形化界面（终端内的交互式界面）。

### 3.2 向导步骤详解

**第 1 步：选择 Agent 平台**
- 选择你用哪个 AI 编程工具：OpenCode / Cursor / Claude Code / Windsurf / GitHub Copilot / Cline / Augment / Trae
- 这决定了后续脚本部署的位置
- **如果不确定，选 OpenCode**

**第 2 步：配置 Vault 路径**
- Vault 是你的 Obsidian 笔记库根目录
- 如果已经在 Obsidian 中打开了一个 vault，直接输入该目录路径
- 如果还没有 vault，建议先创建一个空目录

**第 3 步：配置目录名称**
- **系统目录（system_dir）**：PaperForge 内部文件存放的目录，默认 `99_System`
  - 包含：OCR 结果、Zotero 导出、配置文件
  - 建议保持默认，或改为 `System`
- **资源目录（resources_dir）**：文献笔记存放的目录，默认 `03_Resources`
  - 包含：文献索引、library-records
  - 建议保持默认

**第 4 步：配置 Zotero 数据目录**
- 向导会自动检测 Zotero 数据目录位置
- 如果自动检测失败，手动输入路径：
  - Windows 默认：`C:\Users\你的用户名\Zotero`
  - macOS 默认：`~/Zotero`
- 向导会自动创建 junction/symlink 链接到 vault 内

**第 5 步：配置 PaddleOCR API Key**
- 输入从 https://paddleocr.baidu.com 获取的 API Token
- API URL 保持默认即可：`https://paddleocr.aistudio-app.com/api/v2/ocr/jobs`

**第 6 步：一键部署**
- 向导会自动：
  1. 创建 vault 目录结构
  2. 复制 worker 脚本
  3. 复制精读脚本（ld_deep.py）
  4. 复制图表阅读指南
  5. 复制 Agent 命令文件
  6. 生成 `.env` 配置文件
  7. 生成 `paperforge.json`
  8. 验证文件完整性

### 3.3 安装后文件结构

安装完成后，你的 vault 目录结构如下：

```
your-vault/
├── [system_dir]/                  # 你自定义的系统目录
│   └── PaperForge/
│       ├── exports/               # Better BibTeX JSON 导出（自动生成）
│       ├── ocr/                   # OCR 结果（自动生成）
│       │   └── [zotero_key]/      # 每篇文献一个目录
│       │       ├── meta.json      # OCR 状态
│       │       ├── fulltext.md    # OCR 全文
│       │       ├── images/        # 图表图片
│       │       └── figure-map.json
│       ├── config/
│       │   └── domain-collections.json
│       ├── worker/scripts/        # 工作流脚本
│       └── .env                   # PaddleOCR API Key
│
├── [resources_dir]/               # 你自定义的资源目录
│   └── [literature_dir]/          # 文献笔记
│       └── [domain]/              # 按 Zotero 分类
│           └── [key] - [Title].md # 正式文献笔记
│
├── [control_dir]/                 # 文献状态控制
│   └── library-records/
│       └── [domain]/
│           └── [key].md           # 单条文献状态
│
├── [base_dir]/                    # Obsidian Base 视图
│   └── [domain].base             # 每个分类一个 Base
│
├── [skill_dir]/                   # Agent 技能
│   └── literature-qa/
│       ├── scripts/ld_deep.py
│       ├── prompt_deep_subagent.md
│       └── chart-reading/         # 19 种图表指南
│
├── .env                           # API Key（仅供 CLI 读取）
├── paperforge.json                 # 配置
└── AGENTS.md                       # 本指南
```

---

## 4. 配置 Zotero 和 Better BibTeX

### 4.1 配置 Better BibTeX 自动导出

这一步是关键——PaperForge 通过 Better BibTeX 的自动导出 JSON 来感知 Zotero 中的文献变化。

1. 打开 Zotero → Edit → Preferences → Better BibTeX
2. **勾选 "Keep updated"**（自动导出）
3. **导出格式**：选择 **Better BibLaTeX**
4. **导出路径**设置为：
   ```
   {你的Vault路径}/[system_dir]/PaperForge/exports/library.json
   ```
   例如：`C:\MyVault\99_System\PaperForge\exports\library.json`
5. **点击 OK 保存**

### 4.2 按分类导出（可选）

如果你希望按 Zotero 收藏夹分类导出（推荐），可以：
1. 在 Zotero 中创建多个收藏夹（如：骨科、运动医学、肿瘤学）
2. 在每个收藏夹上右键 → **Export Collection...**
3. 导出为 Better BibLaTeX 格式
4. 保存到 `exports/` 目录：`exports/骨科.json`、`exports/运动医学.json`
5. **勾选 "Keep updated"**

这样 PaperForge 会按分类组织你的文献笔记。

### 4.3 验证 JSON 导出

检查导出文件是否生成：
```powershell
dir {vault_path}/[system_dir]/PaperForge/exports/*.json
```
应该能看到 `.json` 文件。

---

## 5. 验证安装

### 5.1 运行诊断

```powershell
paperforge doctor
```

预期输出包含：
- Python 版本检测 ✓
- Vault 结构检测 ✓
- Zotero 检测 ✓

### 5.2 查看路径

```powershell
paperforge paths
```

显示所有 PaperForge 路径，确认目录结构正确。

### 5.3 查看状态

```powershell
paperforge status
```

显示系统概览，包括：
- PaperForge 版本
- Vault 路径
- 各目录状态
- OCR 配置状态

---

## 6. 首次使用流程

### 6.1 同步 Zotero 文献

```powershell
paperforge sync
```

这个命令会完成两件事：
1. **selection-sync**：读取 BBT JSON 导出，为每篇文献创建 `library-records/[domain]/[key].md`
2. **index-refresh**：生成正式文献笔记 `Literature/[domain]/[key] - [Title].md`，创建 Obsidian Base 视图

预期输出：
```
[INFO] Found 5 new items
[INFO] Created library-records/骨科/XXXXXXX.md
[INFO] Generated 5 formal notes
```

### 6.2 在 Obsidian 中查看

打开 Obsidian，你应该能看到：
- `[resources_dir]/Literature/` 下有了文献笔记
- `[base_dir]/` 下有了 `.base` 文件（Base 视图）
- 在 Obsidian 的 Base 插件中可以看到控制面板

### 6.3 标记要精读的文献

在 Obsidian 中找到 `library-records/[domain]/[key].md`，修改 frontmatter：

```yaml
---
do_ocr: true      # 需要 OCR 提取全文
analyze: true     # 需要精读
---
```

保存后，该文献会进入 OCR 队列。

### 6.4 运行 OCR

```powershell
paperforge ocr
```

新版 `paperforge ocr` 是**一步到位**的：
1. **上传阶段**：将 PDF 上传到 PaddleOCR API
2. **等待阶段**：自动轮询，每 15 秒检查一次进度
3. **下载阶段**：OCR 完成后自动下载全文和图表
4. 全程不需要用户干预

预期输出：
```
Processing OCR: 100%|████| 2/2 [00:00]
Uploading: 100%|████| 2/2 [00:01]
Waiting OCR: 100%|████| 2/2 [00:30]
ocr: updated 2 records
```

输出文件：
- `[system_dir]/PaperForge/ocr/[key]/fulltext.md` — 全文
- `[system_dir]/PaperForge/ocr/[key]/images/` — 图表图片
- `[system_dir]/PaperForge/ocr/[key]/meta.json` — OCR 元数据
- `[system_dir]/PaperForge/ocr/[key]/figure-map.json` — 图表索引

### 6.5 执行精读

在 OpenCode 中（或你选择的 Agent 平台）输入：

```
/pf-deep XXXXXXX
```

Agent 会自动：

**第 1 步：前置准备（prepare）**
- 检查 library-record 状态
- 确认 OCR 已完成
- 生成 figure-map 和 chart-type-map
- 插入 `## 🔍 精读` 骨架（包含所有 figure/table 的 callout 块）
- 每个 callout 块内有 6 个固定子标题

**第 2 步：Pass 1 概览**
- AI 填写"一句话总览"和"5 Cs 快速评估"

**第 3 步：Pass 2 精读还原**
- AI 按顺序逐个填写 figure callout 块
- 每块有固定子标题：图像定位、方法结果、质量审查、作者解释、我的理解、疑点
- AI 读取 chart-type-map，参考对应的图表阅读指南
- 每填写完一张图保存一次
- **完成后自动检查**：顺序、图片边界、空块、缺失子标题

**第 4 步：Pass 3 深度理解**
- AI 编写假设挑战、结论评估、研究启发

**第 5 步：最终验证**
- 运行 validate-note 检查结构完整性

整个精读过程约 5-15 分钟（取决于论文长度），完成后在 Obsidian 中打开文献笔记即可看到 `## 🔍 精读` 区域。

### 6.6 快速摘要（不要求 OCR）

如果只想看论文摘要而不需要完整精读：

```
/pf-paper XXXXXXX
```

这个命令不需要 OCR 完成，只要有正式笔记即可。

---

## 7. 日常使用命令

### 7.1 终端命令

| 命令 | 用途 | 说明 |
|------|------|------|
| `paperforge status` | 查看系统状态 | 诊断各组件健康度 |
| `paperforge sync` | 同步 Zotero 并生成笔记 | 新增/更新文献时运行 |
| `paperforge ocr` | 运行 OCR | 一步到位，等待完成后返回 |
| `paperforge ocr --diagnose` | 诊断 OCR 配置 | 检查 token/URL/API |
| `paperforge deep-reading` | 查看精读队列 | 显示可精读的文献列表 |
| `paperforge doctor` | 诊断整体配置 | 验证安装完整性 |
| `paperforge update` | 更新到最新版 | 自动检测安装方式 |
| `paperforge setup` | 重新运行安装向导 | 修改配置时使用 |
| `paperforge --verbose` | 启用 DEBUG 日志 | 配合任意命令使用 |

### 7.2 Agent 命令（在 OpenCode 中使用）

| 命令 | 用途 |
|------|------|
| `/pf-deep <key>` | 完整三阶段精读 |
| `/pf-paper <key>` | 快速摘要 |
| `/pf-sync` | 同步 Zotero（Agent 解读状态） |
| `/pf-ocr` | 运行 OCR（Agent 检查队列） |
| `/pf-status` | 查看状态（Agent 解读诊断） |

### 7.3 OCR 配置环境变量

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `PADDLEOCR_API_TOKEN` | — | PaddleOCR API Key |
| `PADDLEOCR_JOB_URL` | `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` | API 地址 |
| `PADDLEOCR_MODEL` | `PaddleOCR-VL-1.5` | OCR 模型 |
| `PADDLEOCR_MAX_ITEMS` | 3 | 并发 OCR 数 |
| `PAPERFORGE_RETRY_MAX` | 5 | 上传重试次数 |
| `PAPERFORGE_RETRY_BACKOFF` | 2.0 | 重试退避秒数 |
| `PAPERFORGE_POLL_MAX_CYCLES` | 20 | OCR 轮询最大次数 |
| `PAPERFORGE_POLL_INTERVAL` | 15 | 轮询间隔秒数 |
| `PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES` | 30 | 僵尸任务超时（分钟） |
| `PAPERFORGE_LOG_LEVEL` | INFO | 日志级别 |

---

## 8. 更新 PaperForge

### 8.1 自动更新

```powershell
paperforge update
```

自动检测当前安装方式（pip / pip editable / git clone），执行对应的更新命令。

### 8.2 手动更新

**pip 安装用户：**
```powershell
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

**pip editable 安装用户：**
```powershell
cd {仓库目录}
git pull origin master
pip install -e .
```

**Windows 一键脚本：**
```powershell
.\scripts\install-paperforge.ps1 -Force
```

### 8.3 查看版本

```powershell
python -c "import paperforge; print(paperforge.__version__)"
```

---

## 9. 故障排除

### 9.1 paperforge 命令找不到

```powershell
# 检查 pip 安装
pip list | findstr paperforge

# 如果未安装，重新安装
pip install git+https://github.com/LLLin000/PaperForge.git

# 如果已安装但命令不在 PATH，使用 fallback
python -m paperforge status
```

### 9.2 同步后没有生成 library-records

```
# 检查 JSON 导出文件是否存在
dir {vault}/[system_dir]/PaperForge/exports/*.json

# 确认 JSON 文件有内容
python -c "import json; d=json.loads(open('exports/library.json',encoding='utf-8').read()); print(len(d.get('items',[]) if isinstance(d,dict) else d),'items')"
```

**常见原因：**
- Better BibTeX 自动导出路径配置错误
- JSON 文件为空
- Zotero 中没有带 citation key 的条目

**修复：**
1. Zotero → Edit → Preferences → Better BibTeX → 确认"Keep updated"已勾选
2. 确认导出路径正确
3. 手动在 Zotero 中选一篇文献 → 右键 → Generate BibTeX key

### 9.3 OCR 一直显示 pending

```
# 运行 OCR 诊断
paperforge ocr --diagnose

# 查看具体文献的 OCR 状态
cat {vault}/[system_dir]/PaperForge/ocr/[key]/meta.json
```

**常见原因：**
- PaddleOCR API Key 未配置或无效
- 网络连接问题（API 地址不可达）
- PDF 文件路径错误

**修复：**
- 检查 `.env` 中 `PADDLEOCR_API_TOKEN` 是否正确
- 运行 `paperforge doctor` 查看整体状态

### 9.4 PDF 路径无法解析

```
# 报错信息
ERROR:paperforge.pdf_resolver:PDF path could not be resolved: storage:XXXX/filename.pdf
```

**原因**：Zotero 数据目录链接（junction/symlink）不正确。

**修复：**
1. 确认 Zotero 数据目录位置
2. 重新创建 junction：
```powershell
# 删除旧的链接
rmdir "{vault}/[system_dir]/Zotero"
# 创建新链接（管理员终端）
New-Item -ItemType Junction -Path "{vault}/[system_dir]/Zotero" -Target "C:\Users\用户名\Zotero"
```

或者：
```powershell
# 在 .env 中手动指定 Zotero 数据目录
ZOTERO_DATA_DIR=C:\Users\用户名\Zotero
```

### 9.5 Base 视图不显示数据

- Base 视图需要手动刷新：在 Obsidian 中点击 Refresh 按钮
- 或退出 Obsidian 重新打开

### 9.6 更新后出现异常

```powershell
# 查看完整日志
paperforge status --verbose

# 如果问题持续，重新安装
pip install --force-reinstall git+https://github.com/LLLin000/PaperForge.git
```

---

## 附录

### A. Better BibTeX 配置参考

Zotero → Edit → Preferences → Better BibTeX：

```
☑ Keep updated
Export format: Better BibLaTeX
Export path: {vault}/[system_dir]/PaperForge/exports/library.json
Citation key format: [auth:lower]_[year]
```

### B. paperforge.json 参考

```json
{
  "name": "PaperForge-Lite",
  "version": "1.4.1",
  "repository": "https://github.com/LLLin000/PaperForge",
  "system_dir": "99_System",
  "resources_dir": "03_Resources",
  "literature_dir": "Literature",
  "control_dir": "LiteratureControl",
  "base_dir": "05_Bases",
  "auto_analyze_after_ocr": false,
  "update": {
    "channel": "stable",
    "auto_check": true,
    "check_interval_days": 7
  }
}
```

### C. .env 文件参考

```
PADDLEOCR_API_TOKEN=your_api_token_here
PADDLEOCR_JOB_URL=https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
PADDLEOCR_MODEL=PaddleOCR-VL-1.5
ZOTERO_DATA_DIR=C:\Users\用户名\Zotero
```

### D. 目录名称速查

| 配置项 | 默认值 | 用途 |
|-------|--------|------|
| system_dir | `99_System` | 系统文件 |
| resources_dir | `03_Resources` | 文献资源 |
| literature_dir | `Literature` | 正式笔记 |
| control_dir | `LiteratureControl` | 状态控制 |
| base_dir | `05_Bases` | Obsidian Base |
| skill_dir | `.opencode/skills` | Agent 技能 |
