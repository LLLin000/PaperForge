```
    ______  ___  ______ _________________ ___________ _____  _____
    | ___ \/ _ \ | ___ \  ___| ___ \  ___|  _  | ___ \  __ \|  ___|
    | |_/ / /_\ \| |_/ / |__ | |_/ / |_  | | | | |_/ / |  \/| |__
    |  __/|  _  ||  __/|  __||    /|  _| | | | |    /| | __ |  __|
    | |   | | | || |   | |___| |\ \| |   \ \_/ / |\ \| |_\ \| |___
    \_|   \_| |_/\_|   \____/\_| \_\_|    \___/\_| \_|\____/\____/
```

# PaperForge

[![PyPI version](https://img.shields.io/pypi/v/paperforge?style=for-the-badge&logo=pypi&logoColor=white&color=3775A9)](https://pypi.org/project/paperforge/)
[![Python version](https://img.shields.io/pypi/pyversions/paperforge?style=for-the-badge&logo=python&logoColor=white&color=3775A9)](https://python.org)
[![License](https://img.shields.io/github/license/LLLin000/PaperForge?style=for-the-badge&color=brightgreen)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/LLLin000/PaperForge?style=for-the-badge&logo=github&color=181717)](https://github.com/LLLin000/PaperForge)

> [English](README.md) · **简体中文**

**Obsidian + Zotero + PaddleOCR 驱动的医学文献精读工作流。只需一条命令完成 PDF 上传、OCR 等待、结果下载，自动生成结构化精读笔记。**

```bash
# 首先cd到OB仓库目录
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

*"拿到 PDF 到生成精读笔记，只需要跑两条命令。"*

---

### PaperForge 能为你构建什么

PaperForge 把你的 Zotero 文献库转化为**AI 可直接读取的知识库**：

| 层级 | 产出物 | 用途 |
|------|--------|------|
| **文献索引** | 带结构化 frontmatter 的正式笔记（标题/作者/期刊/DOI/PMID/标签/摘要） | 语义搜索、脱离 Zotero 浏览 |
| **全文语料** | OCR 提取的纯文本 markdown（`fulltext.md`） | 分块 → embedding → RAG，或直接喂给 LLM |
| **图表数据库** | Figure-map（每张图表 = 图片链接 + caption） | 多模态 RAG："展示图 3 并解释" |
| **专家分析** | 结构化精读笔记（Keshav 三阶段 + 图表审查 + 批判评估） | LLM 推理的 ground truth、文献综述、系统评价 |

**这不只是一个笔记工具。** 你的 Vault 会变成一个可查询的知识库，任何 AI 工具（OpenCode、Claude Code、Cursor，或通过 qmd/LlamaIndex 搭建的自定义 RAG 管道）都可以读取、搜索和推理。

---

## 完整工作流程

```
┌──────────────────────────────────────────────────────────┐
│                    文献管理                                │
│                                                          │
│  Zotero 添加新文献                                        │
│    │ Better BibTeX 自动导出 JSON                          │
│    ▼                                                     │
│  paperforge sync  ─── 同步 Zotero → 生成文献笔记            │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                    OCR 全文提取                             │
│                                                          │
│  paperforge ocr    ─── 上传 PDF → 轮询等待 → 下载结果       │
│                          │                                │
│    ┌─────────────────────┼──────────────────────┐         │
│    │ fulltext.md         │ images/              │         │
│    │ OCR 全文文本        │ 图表切割图片         │         │
│    └─────────────────────┴──────────────────────┘         │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                    AI 精读                                 │
│                                                          │
│  /pf-deep <key>  ─── Keshav 三阶段精读                     │
│                          │                                │
│    Pass 1: 概览 ─── 5Cs 快速评估                          │
│    Pass 2: 精读 ─── 按编号逐图解析 + chart-reading 审查     │
│    Pass 3: 深度 ─── 批判评估 + 研究迁移                    │
│                          │                                │
│    ▼                                                     │
│  Obsidian 笔记 ─── ## 🔍 精读 区域已自动填充                │
└──────────────────────────────────────────────────────────┘
```

---

## 功能特性

| 特性 | 说明 |
|------|------|
| **一键 OCR** | `paperforge ocr` 自动上传 → 轮询等待 → 下载结果，一条命令搞定 |
| **三阶段精读** | Keshav 阅读法 + 6 项固定子标题骨架，AI 填空而非自由写作 |
| **图表审查** | 19 种图表类型自动识别 + 专业审查指南 |
| **自动重试** | tenacity 指数退避，网络波动不影响 |
| **结构化日志** | `--verbose` 全局参数，stderr 诊断 |
| **进度指示** | tqdm 进度条 + `--no-progress` |
| **Zotero 同步** | Better BibTeX 自动导出，双工同步 |
| **Obsidian Base** | 文献队列管理，Base 视图集成 |
| **pre-commit 栅栏** | ruff 检查 + 一致性审计 |
| **多平台** | Windows / macOS / Linux |

---

## 快速开始

### 安装

```bash
pip install git+https://github.com/LLLin000/PaperForge.git
paperforge setup
```

安装向导引导你完成：Agent 平台选择、Vault 目录配置、Zotero 数据目录链接、PaddleOCR API Key 配置。详细步骤见 [setup-guide.md](docs/setup-guide.md)。

> Windows 一键安装脚本：
> ```powershell
> powershell -c "iwr -Uri https://raw.githubusercontent.com/LLLin000/PaperForge/master/scripts/install-paperforge.ps1 -OutFile install.ps1; ./install.ps1"
> paperforge setup
> ```

### 前置条件

| 软件 | 用途 | 获取方式 |
|------|------|---------|
| Python 3.10+ | 运行 PaperForge | https://python.org |
| Zotero | 文献管理 | https://zotero.org |
| Better BibTeX | Zotero 插件 | https://retorque.re/zotero-better-bibtex/ |
| Obsidian | 笔记软件 | https://obsidian.md |
| PaddleOCR API Key | OCR 服务 | https://paddleocr.baidu.com |

---

## 命令参考

### 终端命令

| 分类 | 命令 | 用途 |
|------|------|------|
| **安装** | `paperforge setup` | 运行安装向导 |
| | `paperforge doctor` | 诊断配置 |
| **同步** | `paperforge sync` | 同步 Zotero 并生成笔记 |
| **OCR** | `paperforge ocr` | 一键 OCR（上传+等待+下载） |
| | `paperforge ocr --diagnose` | OCR 配置诊断 |
| | `paperforge ocr --no-progress` | 静默模式 |
| **精读** | `paperforge deep-reading` | 查看精读队列 |
| **维护** | `paperforge status` | 系统状态 |
| | `paperforge update` | 自动更新 |
| | `paperforge --verbose` | 全局 DEBUG 日志 |

### Agent 命令（OpenCode 中使用）

| 命令 | 用途 | 前置条件 |
|------|------|---------|
| `/pf-deep <key>` | 完整三阶段精读 | OCR 完成 |
| `/pf-paper <key>` | 快速摘要 | 有正式笔记即可 |
| `/pf-sync` | 同步 Zotero | 安装完成 |
| `/pf-ocr` | 运行 OCR | 安装完成 |
| `/pf-status` | 系统状态 | 安装完成 |

---

## 首次使用

```bash
# 1. 同步 Zotero 文献
paperforge sync

# 2. 在 Obsidian 中标记要精读的文献（设置 do_ocr: true, analyze: true）

# 3. 运行 OCR
paperforge ocr

# 4. 执行精读（在 OpenCode 中输入）
/pf-deep XXXXXXX
```

---

## 更新

```bash
paperforge update
# 或
pip install --upgrade git+https://github.com/LLLin000/PaperForge.git
```

---

## 配置参考

### paperforge.json

```json
{
  "version": "1.4.1",
  "system_dir": "99_System",
  "resources_dir": "03_Resources",
  "literature_dir": "Literature",
  "control_dir": "LiteratureControl",
  "base_dir": "05_Bases",
  "auto_analyze_after_ocr": false
}
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PADDLEOCR_API_TOKEN` | — | PaddleOCR API Key |
| `PADDLEOCR_JOB_URL` | `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` | API 地址 |
| `PAPERFORGE_LOG_LEVEL` | `INFO` | 日志级别 |
| `PAPERFORGE_RETRY_MAX` | `5` | 上传重试次数 |
| `PAPERFORGE_POLL_MAX_CYCLES` | `20` | 轮询最大次数 |

---

## 文档

| 文档 | 用途 |
|------|------|
| [📖 详细安装配置指南](docs/setup-guide.md) | 从零开始的完整教程 |
| [⚡ 快速安装指南](docs/INSTALLATION.md) | 简洁版安装步骤 |
| [📋 安装后指南](AGENTS.md) | 第一次使用必看 |
| [📝 变更日志](CHANGELOG.md) | 版本历史 |
| [🤝 贡献指南](CONTRIBUTING.md) | 开发环境搭建 |


---

## License

MIT License
