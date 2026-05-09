<p align="center">
  <img src="docs/images/paperforge-banner.png" alt="PaperForge banner" width="100%" />
</p>

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

**简体中文** · [English](README.en.md)

> **铸知识为器，启洞见之明。 — Forge Knowledge, Empower Insight.**

PaperForge 让你在 Obsidian 里管理 Zotero 文献。同步、OCR 全文提取、图表解析、AI 精读，全在一个 Vault 里完成。

---

## 0. 先理解它是什么

PaperForge **不是一个纯 Obsidian 插件**。它有两部分：

| 部分 | 是什么 | 干什么 | 装在哪 |
|------|--------|--------|--------|
| Obsidian 插件 | `main.js` + `manifest.json` + `styles.css` | Dashboard、按钮、设置界面 | Vault 的 `.obsidian/plugins/paperforge/` |
| Python 包 | `paperforge` | 同步、OCR、Doctor、修复 | 系统 Python 环境 (`pip install`) |

插件是**壳**，Python 包是**引擎**。插件里的按钮点了之后，实际是调用 Python 命令行去干活。

**所以装完插件之后，必须在设置里确认 Python 包也已安装，并且版本一致。**

---

## 1. 安装 Obsidian 插件

### 方式一：BRAT（推荐）

1. 在 Obsidian 社区插件市场搜索安装 **BRAT**（Beta Reviewer's Auto-update Tester）
2. 打开 BRAT 设置 → `Add Beta Plugin`
3. 填入仓库地址：`https://github.com/LLLin000/PaperForge`
4. BRAT 会自动下载最新 Release 的 `main.js`、`manifest.json`、`styles.css` 并安装
5. 在 Obsidian 设置 → 社区插件 → 启用 PaperForge

> BRAT 能自动检测 GitHub Release 更新，不需要手动下载。

### 方式二：手动下载

1. 打开 [Releases](https://github.com/LLLin000/PaperForge/releases) 页面
2. 下载最新版本的三个文件：`main.js`、`manifest.json`、`styles.css`
3. 在 Vault 里创建文件夹 `.obsidian/plugins/paperforge/`
4. 把三个文件放进去
5. 重启 Obsidian → 设置 → 社区插件 → 启用 PaperForge

> 手动安装不会自动更新，每次新版本需要重新下载替换。

---

## 2. 安装 Python 包

插件装好后，打开 PaperForge 设置页面。你会看到 **运行时状态** 区域：

```
插件 v1.4.17 → Python 包 v1.4.17 ✓ 匹配
```

- 如果显示"未安装" → 点击 **同步运行时** 按钮，或者自己在终端执行：
  ```bash
  pip install --upgrade git+https://github.com/LLLin000/PaperForge.git@1.4.17
  ```
- 如果显示"版本不匹配" → 说明插件版本和 Python 包版本不一致。点"同步运行时"会自动拉取与插件版本匹配的 Python 包。

---

## 3. Python 解释器识别逻辑

PaperForge 需要找到你系统里的 Python。它按以下顺序查找，找到就用：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | **你手动指定** | 设置 → `自定义 Python 路径`，填入完整路径（如 `C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\python.exe`）。**这是最可靠的方式。** |
| 2 | **venv 自动检测** | 自动扫描 Vault 根目录下的 `.paperforge-test-venv`、`.venv`、`venv` 里的 Python |
| 3 | **系统自动检测** | 依次尝试 `py -3`、`python`、`python3`，用 `--version` 验证，挑第一个能用的 |
| 4 | **兜底** | 以上都找不到，回退到 `python` |

> 如果你系统里有多个 Python（比如系统自带的 3.9 + 自己装的 3.11），**强烈建议在设置里手动指定路径**，避免跑错环境。
>
> 设置里的 **验证** 按钮会立即测试当前选中的解释器，显示它能不能用、是什么版本。

---

## 4. 安装向导参数说明

`Ctrl+P` → `PaperForge: Run Setup Wizard` 会引导你配置以下内容。每一步都解释在这里，免得你填的时候不知道是什么意思。

### 4.1 Vault 路径
你当前打开的 Obsidian Vault 根目录。安装向导自动检测，一般不用改。

### 4.2 AI Agent 平台

PaperForge 的精读功能通过 AI Agent 执行（如 `/pf-deep` 命令）。你需要选择你使用的 Agent 平台，安装向导会把对应的命令文件部署到正确位置。

| Agent | 命令文件放在 | 前缀 | 如何触发精读 |
|-------|-------------|------|------------|
| **OpenCode** | `.opencode/command/` + `.opencode/skills/` | `/` | 打开 OpenCode，输入 `/pf-deep <key>` |
| **Claude Code** | `.claude/skills/` | `/` | 打开 Claude Code，输入 `/pf-deep <key>` |
| **Cursor** | `.cursor/skills/` | `/` | 打开 Cursor 的 AI Chat，输入 `/pf-deep <key>` |
| **GitHub Copilot** | `.github/skills/` | `/` | 打开 Copilot Chat，输入 `/pf-deep <key>` |
| **Windsurf** | `.windsurf/skills/` | `/` | 打开 Windsurf，输入 `/pf-deep <key>` |
| **Codex** | `.codex/skills/` | `$` | 打开 Codex，输入 `$pf-deep <key>` |
| **Cline** | `.clinerules/` | `/` | 打开 Cline，输入 `/pf-deep <key>` |

> 注意：`/pf-deep` 和 `/pf-paper` **不是在终端里执行的命令**。你需要先启动对应的 Agent 应用（比如打开 OpenCode），然后在这个 Agent 的对话输入框里输入命令，Agent 才会调用 PaperForge 的精读脚本去分析你的论文。

### 4.3 目录命名

安装向导会问你几个目录叫什么名字。这些都是给你自己看的，用来组织 Vault 里的文件结构。**大部分情况用默认值就行。**

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `system_dir` | `99_System` | PaperForge 内部数据的总目录。下面会有 `exports/`（Zotero 导出的 JSON）、`ocr/`（OCR 结果）、`config/` 等子目录。你一般不需要手动进去看。 |
| `resources_dir` | `03_Resources` | 资源根目录。你的正式文献笔记就放在这里下面的 `literature_dir` 里。 |
| `literature_dir` | `Literature` | 正式文献笔记的目录。`paperforge sync` 生成的带 frontmatter 的 `.md` 笔记在这里。你日常阅读、编辑笔记都在这个目录。 |
| `base_dir` | `05_Bases` | Obsidian Base 视图文件目录。Dashboard 里的筛选视图（"待 OCR"、"待精读"等）存在这里。 |

### 4.4 PaddleOCR API Token

OCR 功能需要 PaddleOCR 的 API。在 `.env` 文件里配置：

```
PADDLEOCR_API_TOKEN=你的API密钥
```

安装向导会引导你填写，也可以之后手动在 Vault 根目录的 `.env` 文件里加。OCR URL 一般不需要改。

### 4.5 Zotero 数据目录

PaperForge 会创建一个 junction（Windows）或 symlink（macOS/Linux），把 Zotero 的数据目录连接到 Vault 里。这样 Obsidian 的 wikilink 才能找到 PDF 文件。

安装向导会自动检测 Zotero 的安装位置。如果检测失败，你需要手动指定 Zotero 数据目录的路径——也就是包含 `storage` 子目录的那个文件夹（不是 Zotero 程序本身）。

### 4.6 安装过程

确认配置后，安装向导会自动：
- 创建所有需要的目录结构
- 把 Agent 命令文件部署到对应位置
- 把 Obsidian 插件文件安装到位
- 创建 Zotero junction/symlink
- 写入 `paperforge.json` 和 `.env`

整个过程是**增量的** — 如果你选的目录里已经有文件，安装向导只会补充缺失的，不会删除已有内容。

---

## 5. 首次使用

1. **确认版本一致**：设置 → 运行时状态 → 确保插件和 Python 包版本一致
2. **确认 Python 正确**：设置 → 验证按钮，确认连接的是你想要的 Python
3. **运行安装向导**：`Ctrl+P` → `PaperForge: Run Setup Wizard`
4. **配置 PaddleOCR**：在 `.env` 里填入 API Token（安装向导会引导你做这一步）
5. **在 Zotero 里导出文献**：右键要同步的文献库 → `导出...` → 格式选 `Better BibTeX JSON` → 勾选 `Keep updated` → 保存到 `<system_dir>/PaperForge/exports/`
6. **运行 Doctor**：Dashboard → `Run Doctor`，确认所有检查通过

---

## 6. 日常使用

所有机械操作都可以从 Obsidian Dashboard 完成：

| 你要做什么 | 操作 |
|-----------|------|
| 打开控制面板 | `Ctrl+P` → `PaperForge: Open Dashboard` |
| 同步 Zotero 文献 | Dashboard → `Sync Library` |
| 运行 OCR | Dashboard → `Run OCR` |
| 检查系统状态 | Dashboard → `Run Doctor` |

### AI 精读（需 Agent）

| 命令 | 作用 | 前置条件 |
|------|------|---------|
| `/pf-deep <zotero_key>` | 完整三阶段精读 | OCR 完成、analyze 设为 true |
| `/pf-paper <zotero_key>` | 快速文献摘要 | 已有正式笔记 |
| `/pf-sync` | Agent 帮你同步 Zotero | 已安装 |
| `/pf-ocr` | Agent 帮你运行 OCR | 已安装 |
| `/pf-status` | Agent 帮你查看状态 | 已安装 |

> **使用方式**：打开你选择的 Agent 应用（OpenCode / Claude Code / Cursor / …），在对话输入框里输入这些命令。不同的 Agent 前缀可能不同（大部分是 `/`，Codex 是 `$`）。

---

## 7. 完整工作流

```
Zotero 添加论文
  ↓ Better BibTeX 自动导出 JSON 到 exports/ 目录
Dashboard → Sync Library
  ↓ 生成正式笔记（Literature/ 目录下，带 frontmatter 元数据）
在笔记 frontmatter 里把 do_ocr 设为 true
  ↓
Dashboard → Run OCR
  ↓ PaddleOCR 提取全文 + 图表 → ocr/ 目录
在笔记 frontmatter 里把 analyze 设为 true
  ↓
打开 Agent → 输入 /pf-deep <zotero_key>
  ↓ Agent 执行三阶段精读
笔记里出现 ## 🔍 精读 区域
```

---

## 8. 常见问题

### 插件加载失败（Cannot find module）

- 确认 `.obsidian/plugins/paperforge/` 下有 `main.js`、`manifest.json`、`styles.css` 三个文件
- 如果 BRAT 从旧版升级后出问题：删除整个 `paperforge` 插件文件夹，让 BRAT 重新下载
- 打开 Developer Console（`Ctrl+Shift+I`）看红色报错

### "同步运行时" 点了还是旧版本

- 插件调用的 Python 可能和你终端用的是不同环境。检查设置 → Python 解释器路径
- pip 缓存问题，用 `--no-cache-dir` 重装
- 确认 `https://github.com/LLLin000/PaperForge` 网络能通

### OCR 一直 pending

- 确认 `.env` 里有 `PADDLEOCR_API_TOKEN`
- 终端运行 `paperforge ocr --diagnose` 检查 API 连通性
- PDF 路径可能不对：运行 `paperforge repair --fix-paths`

### 同步后没有生成笔记

- Zotero Better BibTeX 是否配置了自动导出？JSON 是否在 `exports/` 目录？
- 运行 `paperforge doctor` 看具体哪一步失败

### /pf-deep 命令没反应

- 确认你在 Agent 软件里执行，不是在终端
- 确认 OCR 已完成（ocr_status: done）
- 确认 analyze 已设为 true

---

## 9. 更新

BRAT 会自动检测插件更新。Python 包更新：

```bash
paperforge update
# 或
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

---

## 10. 架构

```
paperforge/
├── core/          契约层 — PFResult/ErrorCode/状态机
├── adapters/      适配器层 — BBT 解析、路径、frontmatter
├── services/      服务层 — SyncService 编排
├── worker/        工人层 — OCR、状态、修复
├── commands/      CLI 分发
├── setup/         安装向导（目录创建、Agent 部署、Zotero 链接）
├── plugin/        Obsidian 插件（Dashboard、设置面板）
└── schema/        字段注册表
```

---

## 协议

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)。仅限非商业使用。

## 致谢

基于 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)、[Obsidian](https://obsidian.md)、[Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/) 等开源项目构建。
