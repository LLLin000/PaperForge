```
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/
```

# PaperForge

[![Version](https://img.shields.io/github/v/release/LLLin000/PaperForge?style=for-the-badge&label=version)](https://github.com/LLLin000/PaperForge/releases)
[![Python](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgreen?style=for-the-badge)](LICENSE)

> [English](README.md) · **简体中文**

**Obsidian + Zotero 文献管理流水线。安装一个插件，全程无需终端。**

```text
下载插件 → Obsidian 中启用 → 打开安装向导 → 填写配置 → 点安装 → 完成
```

*"从 PDF 到结构化精读笔记，全在 Obsidian 内完成。"*

---

## PaperForge 能做什么

把你的 Zotero 文献库转化为 AI 可直接读取的知识库：

| 层级 | 产出 | 用途 |
|------|------|------|
| **索引卡片** | 带结构化 frontmatter 的索引记录（标题/作者/期刊/DOI/标签/摘要） | 搜索、浏览、Base 视图筛选 |
| **全文语料** | OCR 提取的纯文本 markdown（`fulltext.md`） | 喂给 LLM、RAG、问答 |
| **图表数据库** | 每张图表的图片链接 + 说明文字 | 多模态分析："展示图 3 并解释" |
| **精读笔记** | AI 写作的三阶段分析 + 图表审查 + 批判评估 | 文献综述、系统评价 |

---

## 安装

### Obsidian 插件（推荐）

1. **下载**插件文件：[最新 Release](https://github.com/LLLin000/PaperForge/releases/latest)

2. **放入** Vault 目录：`{vault}/.obsidian/plugins/paperforge/`

3. **启用**：Obsidian → 设置 → 第三方插件 → PaperForge

4. **打开安装向导**：设置 → PaperForge → "打开安装向导"

5. **跟随 5 步向导**：概览 → 目录配置 → Agent 与密钥 → 安装 → 完成

> 安装向导会自动检测 Python、Zotero、Better BibTeX 是否就绪。

### 前置准备

| 软件 | 用途 | 获取 |
|------|------|------|
| Python 3.9+ | 运行 PaperForge CLI | https://python.org |
| Zotero | 文献管理 | https://zotero.org |
| Better BibTeX | Zotero 插件（JSON 导出） | https://retorque.re/zotero-better-bibtex/ |
| PaddleOCR Key | OCR 文字识别 | https://aistudio.baidu.com/paddleocr |

### 命令行安装（高级用户）

```bash
cd /path/to/your/vault
pip install git+https://github.com/LLLin000/PaperForge.git
python -m paperforge setup --headless --agent opencode --paddleocr-key <key>
```

---

## 使用方式（全在 Obsidian 内）

| 操作 | 方式 |
|------|------|
| **打开面板** | `Ctrl+P` → "PaperForge: Open Dashboard"，或点左侧书本图标 |
| **同步文献** | 面板中点击 "Sync Library" — 从 Zotero 拉取文献，生成索引卡片和正文笔记 |
| **运行 OCR** | 面板中点击 "Run OCR" — 提取 PDF 全文和图表 |
| **AI 精读** | `/pf-deep <zotero_key>` — AI 三阶段深度分析（需在 AI Agent 中执行） |
| **快速查询** | `/pf-paper <zotero_key>` — 快速文献问答 |

### Dashboard 面板

```
┌──────────────────────────────────┐
│  PaperForge                   ↻  │
│                                  │
│  [Papers: 550] [Notes: 520] [...]│
│                                  │
│  OCR Pipeline  [Active]          │
│  ████████████░░░░░░░░ 80%        │
│  Pending: 10  Active: 2  Done: 8│
│                                  │
│  Quick Actions                   │
│  [Sync Library] [Run OCR]        │
└──────────────────────────────────┘
```

---

## 命令参考

### Obsidian 命令面板（`Ctrl+P`）

| 命令 | 说明 |
|------|------|
| `PaperForge: Open Dashboard` | 打开状态面板 |
| `PaperForge: Sync Library` | 同步 Zotero 生成笔记 |
| `PaperForge: Run OCR` | 提取全文和图表 |

### Agent 命令

| 命令 | 说明 | 前置条件 |
|------|------|---------|
| `/pf-deep <key>` | 完整三阶段精读 | OCR 完成 |
| `/pf-paper <key>` | 快速文献问答 | 有正式笔记 |
| `/pf-sync` | 同步 Zotero | 已安装 |
| `/pf-ocr` | 运行 OCR | 已安装 |
| `/pf-status` | 系统状态 | 已安装 |

### 终端命令（可选）

| 命令 | 说明 |
|------|------|
| `paperforge sync` | 同步 Zotero 生成笔记 |
| `paperforge ocr` | 运行 OCR |
| `paperforge status` | 系统概览 |
| `paperforge doctor` | 诊断配置 |
| `paperforge update` | 自动更新 |

---

## 支持的 Agent 平台

| 平台 | Agent 命令 | 部署位置 |
|------|-----------|---------|
| **OpenCode** | 完整支持（所有 `/pf-*` 命令） | `.opencode/command/` + `.opencode/skills/` |
| **Claude Code** | `/pf-deep`, `/pf-paper` | `.claude/skills/` |
| **Cursor** | `/pf-deep`, `/pf-paper` | `.cursor/skills/` |
| **GitHub Copilot** | `/pf-deep`, `/pf-paper` | `.github/skills/` |
| **Windsurf** | `/pf-deep`, `/pf-paper` | `.windsurf/skills/` |
| **Codex** | `$pf-deep`, `$pf-paper` | `.codex/skills/` |
| **Cline** | `/pf-deep`, `/pf-paper` | `.clinerules/` |

在安装向导中选择你的平台，文件会自动部署。

---

## 配置

安装向导会处理所有配置。生成的文件结构：

```
vault/
├── paperforge.json          ← 目录配置 + Agent 平台
├── System/
│   └── PaperForge/
│       ├── .env             ← PaddleOCR API Key
│       ├── exports/         ← Better BibTeX JSON 导出放这里
│       └── config/          ← domain-collections.json
├── Resources/
│   ├── Notes/               ← 正文笔记（元数据 + 精读笔记）
│   └── Index_Cards/         ← 索引卡片（按领域分文件夹）
└── Base/                   ← Obsidian Base 视图
```

环境变量（可选覆盖）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PADDLEOCR_API_TOKEN` | — | PaddleOCR API Key |
| `PAPERFORGE_LOG_LEVEL` | `INFO` | 日志级别 |

---

## 更新

每次 Obsidian 重启自动更新（可在插件设置中关闭）。或手动：

```bash
paperforge update
# 或
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [安装指南](docs/setup-guide.md) | 从零开始的完整教程 |
| [快速安装](docs/INSTALLATION.md) | 简洁版安装步骤 |
| [安装后指南](AGENTS.md) | 首次使用必看 |
| [变更日志](CHANGELOG.md) | 版本历史 |
| [贡献指南](CONTRIBUTING.md) | 开发环境搭建 |

---

## 协议

[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) — 开源非商用。
详见 [LICENSE](LICENSE)。

---

## 致谢

PaperForge 站在这些优秀项目的肩膀上：

| 项目 | 作用 |
|------|------|
| [PaddleOCR / PaddleOCR-VL](https://github.com/PaddlePaddle/PaddleOCR) | PDF OCR 引擎 — 文字提取、版面检测、图表分割 |
| [Obsidian](https://obsidian.md) | 笔记平台 — 插件宿主、Vault 文件系统 |
| [Better BibTeX for Zotero](https://retorque.re/zotero-better-bibtex/) | 文献数据自动导出为 JSON |
| [PyMuPDF (fitz)](https://github.com/pymupdf/PyMuPDF) | 本地 PDF 验证与净化 |
| [requests](https://github.com/psf/requests) | OCR API HTTP 客户端 |
| [tenacity](https://github.com/jd/tenacity) | 指数退避重试机制 |
| [Pillow](https://python-pillow.org) | 图表图片处理 |
| [tqdm](https://github.com/tqdm/tqdm) | 进度条 |
| [textual](https://github.com/Textualize/textual) | TUI 组件（诊断向导） |
